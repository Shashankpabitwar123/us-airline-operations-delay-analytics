#!/usr/bin/env python3
"""Incrementally ingest BTS monthly releases and rebuild the shared analytical layer.

Usage: python scripts/refresh.py --through 2026-06
The initial historical parquet is optional: without it all requested months are downloaded.
No credentials, paid API, or Tableau Cloud account is required.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path
import duckdb
import pandas as pd
from legacy_bts_loader import process_chunk, CANDIDATES, source_url

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; PROCESSED=DATA/'processed'; EXPORT=DATA/'exports'

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def dump(path,value):
    path.write_text(json.dumps(value,indent=2,default=str,allow_nan=False)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--through',default='2026-06');args=ap.parse_args()
    end=datetime.strptime(args.through,'%Y-%m')
    for p in [PROCESSED,EXPORT,DATA/'raw_cache',DATA/'reference',ROOT/'docs/evidence']:p.mkdir(parents=True,exist_ok=True)
    manifest_path=DATA/'source_manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'sources':[]}
    sources={s['partition']:s for s in manifest['sources']}
    if end.year < 2023: ap.error('--through must be January 2023 or later')
    historical=PROCESSED/'historical_2023_2025.parquet'
    use_historical=historical.exists() and end >= datetime(2025,12,1)
    if use_historical:
        sources['2023-2025']={'partition':'2023-2025','kind':'inherited flight-level processed snapshot','rows':20928579,'sha256':digest(historical),'source':'BTS Reporting Carrier, 36 monthly files','note':'Original project snapshot. Original ZIP hashes were not retained; corrections derive from recorded arrival minutes, not legacy flags.'}
    paths=[historical] if use_historical else []
    loaded_partitions=['2023-2025'] if use_historical else []
    for year in range(2023,end.year+1):
        for month in range(1,13):
            if (year,month)>(end.year,end.month):break
            if use_historical and year<=2025:continue
            key=f'{year}-{month:02d}'; loaded_partitions.append(key); out=PROCESSED/f'flights_{key}.parquet';paths.append(out)
            if out.exists() and key in sources:continue
            zpath=DATA/'raw_cache'/f'bts_{year}_{month:02d}.zip'
            if not zpath.exists():
                print('Downloading',key,flush=True);tmp=zpath.with_suffix('.download')
                urllib.request.urlretrieve(source_url(year,month),tmp);tmp.replace(zpath)
            pieces=[];raw_count=0
            with zipfile.ZipFile(zpath) as z:
                name=next(n for n in z.namelist() if n.lower().endswith('.csv'))
                with z.open(name) as f:
                    for chunk in pd.read_csv(f,usecols=lambda c:c in CANDIDATES,chunksize=250000,low_memory=False):
                        raw_count+=len(chunk);pieces.append(process_chunk(chunk))
            frame=pd.concat(pieces,ignore_index=True)
            if len(frame)!=raw_count:raise ValueError(f'{key}: required keys dropped {raw_count-len(frame)} records')
            frame.to_parquet(out,index=False,compression='zstd')
            sources[key]={'partition':key,'url':source_url(year,month),'raw_rows':raw_count,'rows':len(frame),'zip_sha256':digest(zpath),'parquet_sha256':digest(out),'retrieved_at':datetime.now(timezone.utc).isoformat()}
            print('Ingested',key,len(frame),flush=True)
            manifest['sources']=list(sources.values());dump(manifest_path,manifest)
    manifest['sources']=list(sources.values());manifest['through']=args.through;manifest['active_partitions']=loaded_partitions;dump(manifest_path,manifest)
    con=duckdb.connect(str(PROCESSED/'flightpath.duckdb'));con.execute("SET threads=4")
    files=', '.join("'"+str(p).replace("'","''")+"'" for p in paths)
    con.execute(f"CREATE OR REPLACE VIEW source_flights AS SELECT * FROM read_parquet([{files}],union_by_name=true)")
    con.execute("""CREATE OR REPLACE TABLE fact_flights AS
    WITH typed AS (SELECT * EXCLUDE(arrived_on_time,delayed_flight,departure_period,delay_severity),
      try_cast(split_part(flight_key,'|',6) AS INTEGER) AS scheduled_departure_hhmm
      FROM source_flights), hours AS (SELECT *,
      CASE WHEN scheduled_departure_hhmm=2400 THEN 0
           WHEN scheduled_departure_hhmm BETWEEN 0 AND 2359 AND scheduled_departure_hhmm%100<60
           THEN scheduled_departure_hhmm//100 ELSE NULL END AS departure_hour,
      CASE WHEN cancelled=0 AND diverted=0 AND arrival_delay_minutes IS NOT NULL THEN 1 ELSE 0 END AS eligible_arrival
      FROM typed)
    SELECT *,
      CASE WHEN eligible_arrival=1 AND arrival_delay_minutes<15 THEN 1 ELSE 0 END AS arrived_on_time,
      CASE WHEN eligible_arrival=1 AND arrival_delay_minutes>=15 THEN 1 ELSE 0 END AS delayed_flight,
      CASE WHEN eligible_arrival=1 AND arrival_delay_minutes>=60 THEN 1 ELSE 0 END AS severe_delay,
      CASE WHEN eligible_arrival=1 AND arrival_delay_minutes>=120 THEN 1 ELSE 0 END AS extreme_delay,
      CASE WHEN departure_hour<6 THEN 'Overnight' WHEN departure_hour<11 THEN 'Morning'
           WHEN departure_hour<15 THEN 'Midday' WHEN departure_hour<19 THEN 'Afternoon'
           WHEN departure_hour<24 THEN 'Evening' ELSE 'Unknown' END AS departure_period,
      CASE WHEN cancelled=1 THEN 'Cancelled' WHEN diverted=1 THEN 'Diverted' WHEN eligible_arrival=0 THEN 'Missing arrival'
           WHEN arrival_delay_minutes<15 THEN 'Under 15 min' WHEN arrival_delay_minutes<30 THEN '15-29 min'
           WHEN arrival_delay_minutes<60 THEN '30-59 min' WHEN arrival_delay_minutes<120 THEN '60-119 min' ELSE '120+ min' END AS outcome
    FROM hours""")
    # Small reference data enriches geographic labels without inventing missing coordinates.
    apath=DATA/'reference/airport_codes.csv'
    if not apath.exists():urllib.request.urlretrieve('https://raw.githubusercontent.com/datasets/airport-codes/master/data/airport-codes.csv',apath)
    con.execute(f"CREATE OR REPLACE VIEW airport_reference_raw AS SELECT * FROM read_csv_auto('{apath}',all_varchar=true)")
    con.execute("""CREATE OR REPLACE TABLE airport_reference AS SELECT iata_code, name,
      try_cast(split_part(coordinates,',',2) AS DOUBLE) AS longitude,
      try_cast(split_part(coordinates,',',1) AS DOUBLE) AS latitude
      FROM airport_reference_raw WHERE iata_code IS NOT NULL
      QUALIFY row_number() OVER(PARTITION BY iata_code ORDER BY CASE type WHEN 'large_airport' THEN 0 WHEN 'medium_airport' THEN 1 WHEN 'small_airport' THEN 2 ELSE 3 END,ident)=1""")
    # Preserve the historical BTS code after the current reference changed its identifier.
    # OurAirports KPBI historical facility page: https://ourairports.com/airports/KPBI/frequencies.html
    con.execute("INSERT INTO airport_reference SELECT 'PBI','Palm Beach International Airport',-80.095596,26.683201 WHERE NOT EXISTS(SELECT 1 FROM airport_reference WHERE iata_code='PBI')")
    con.execute("""CREATE OR REPLACE TABLE dim_airport AS
      WITH airports AS (SELECT origin_airport_key AS airport_key,origin AS airport_code,origin_city_name AS city_name,origin_state AS state_code FROM fact_flights
      UNION SELECT dest_airport_key,dest,dest_city_name,dest_state FROM fact_flights)
      SELECT a.*,coalesce(r.name,a.city_name) AS airport_name,r.latitude,r.longitude FROM airports a LEFT JOIN airport_reference r ON a.airport_code=r.iata_code""")
    # DOT stable IDs prevent carrier-code reuse from silently merging different airlines.
    labels={19393:'Southwest Airlines',19690:'Hawaiian Airlines',19790:'Delta Air Lines',19805:'American Airlines',19930:'Alaska Airlines',19977:'United Airlines',20304:'SkyWest Airlines',20363:'Endeavor Air',20368:'Allegiant Air',20397:'PSA Airlines',20398:'Envoy Air',20409:'JetBlue Airways',20416:'Spirit Airlines',20436:'Frontier Airlines',20452:'Republic Airways'}
    carrier_rows=con.execute('SELECT DISTINCT airline_key,reporting_airline FROM fact_flights ORDER BY 1').fetchall()
    con.execute('CREATE OR REPLACE TABLE dim_airline(airline_key BIGINT,carrier_code VARCHAR,carrier_name VARCHAR)')
    con.executemany('INSERT INTO dim_airline VALUES (?,?,?)',[(k,c,labels.get(k,c)) for k,c in carrier_rows])
    # Counts are additive; every displayed rate is rebuilt from its numerator and denominator.
    sums="""count(*) AS scheduled_flights,sum(eligible_arrival) AS eligible_arrivals,sum(arrived_on_time) AS on_time_flights,
    sum(delayed_flight) AS delayed_flights,sum(cancelled) AS cancelled_flights,sum(diverted) AS diverted_flights,
    sum(severe_delay) AS severe_flights,sum(extreme_delay) AS extreme_flights,
    sum(CASE WHEN eligible_arrival=1 THEN greatest(arrival_delay_minutes,0) ELSE 0 END) AS arrival_delay_minutes,
    sum(carrier_delay) AS carrier_minutes,sum(weather_delay) AS weather_minutes,sum(nas_delay) AS nas_minutes,
    sum(security_delay) AS security_minutes,sum(late_aircraft_delay) AS late_aircraft_minutes"""
    specs={'monthly':'year,month','hourly':'year,month,departure_hour','airport_monthly':'year,month,origin',
      'carrier_monthly':'year,month,airline_key','route_monthly':'year,month,origin,dest',
      'airport_hourly':'year,month,origin,departure_hour','outcomes':'year,month,outcome'}
    for name,group in specs.items():
        con.execute(f'CREATE OR REPLACE TABLE {name} AS SELECT {group},{sums} FROM fact_flights GROUP BY {group} ORDER BY {group}')
    con.execute(f"""CREATE OR REPLACE TABLE tableau_operations AS
      WITH summary AS (SELECT year,month,origin,dest,airline_key,departure_period,{sums} FROM fact_flights GROUP BY year,month,origin,dest,airline_key,departure_period)
      SELECT s.*,a.airport_name AS origin_name,a.city_name AS origin_city,a.state_code AS origin_state,a.latitude AS origin_latitude,a.longitude AS origin_longitude,
      d.airport_name AS destination_name,d.latitude AS destination_latitude,d.longitude AS destination_longitude,c.carrier_name,
      make_date(year,month,1) AS month_start, origin||' → '||dest AS route,
      CASE WHEN year=2026 THEN '2026 YTD' ELSE 'Complete year' END AS coverage
      FROM summary s LEFT JOIN dim_airport a ON s.origin=a.airport_code LEFT JOIN dim_airport d ON s.dest=d.airport_code LEFT JOIN dim_airline c USING(airline_key)""")
    # Compare morning/evening on the same directional route, carrier and month.
    con.execute("""CREATE OR REPLACE TABLE matched_dayparts AS
      WITH g AS (SELECT year,month,origin,dest,airline_key,
      sum(eligible_arrival) FILTER(WHERE departure_period='Morning') AS morning_n,
      sum(delayed_flight) FILTER(WHERE departure_period='Morning') AS morning_delayed,
      sum(eligible_arrival) FILTER(WHERE departure_period='Evening') AS evening_n,
      sum(delayed_flight) FILTER(WHERE departure_period='Evening') AS evening_delayed
      FROM fact_flights GROUP BY 1,2,3,4,5)
      SELECT *,morning_delayed*1.0/morning_n AS morning_rate,evening_delayed*1.0/evening_n AS evening_rate,
      evening_delayed*1.0/evening_n-morning_delayed*1.0/morning_n AS gap,
      least(morning_n,evening_n) AS common_weight
      FROM g WHERE morning_n>=30 AND evening_n>=30""")
    con.execute("""CREATE OR REPLACE TABLE carrier_peers AS
      WITH g AS (SELECT year,month,origin,dest,airline_key,sum(eligible_arrival) AS n,sum(delayed_flight) AS delayed
      FROM fact_flights GROUP BY 1,2,3,4,5 HAVING sum(eligible_arrival)>=100),p AS (
      SELECT *,sum(n) OVER(PARTITION BY year,month,origin,dest)-n AS peer_n,
      sum(delayed) OVER(PARTITION BY year,month,origin,dest)-delayed AS peer_delayed,
      count(*) OVER(PARTITION BY year,month,origin,dest) AS carrier_count FROM g)
      SELECT *,delayed*1.0/n AS delay_rate,peer_delayed*1.0/peer_n AS peer_rate,
      delayed*1.0/n-peer_delayed*1.0/peer_n AS gap FROM p WHERE carrier_count>=2 AND peer_n>=100""")
    profile=con.execute("""SELECT count(*) AS fact_rows,count(distinct flight_key) AS unique_keys,count(distinct flight_month) AS month_count,
      min(flight_date) AS min_date,max(flight_date) AS max_date,sum(eligible_arrival) AS eligible_arrivals,
      sum(cancelled) AS cancelled_flights,sum(diverted) AS diverted_flights,
      count(*) FILTER(WHERE cancelled=0 AND diverted=0 AND arrival_delay_minutes IS NULL) AS missing_arrivals,
      count(*) FILTER(WHERE departure_hour IS NULL) AS missing_departure_hours FROM fact_flights""").fetchdf().iloc[0].to_dict()
    tests=[]
    def check(name,actual,expected):
        tests.append({'check':name,'actual':int(actual),'expected':int(expected),'passed':int(actual)==int(expected)})
    expected=sum(sources[key]['rows'] for key in loaded_partitions)
    check('source rows to fact',profile['fact_rows'],expected)
    check('candidate key uniqueness',profile['unique_keys'],profile['fact_rows'])
    check('monthly coverage',profile['month_count'],(end.year-2023)*12+end.month)
    check('outcome reconciliation',sum(profile[k] for k in ['eligible_arrivals','cancelled_flights','diverted_flights','missing_arrivals']),profile['fact_rows'])
    for table in [*specs,'tableau_operations']:
        check(table+' scheduled reconciliation',con.execute(f'select sum(scheduled_flights) from {table}').fetchone()[0],profile['fact_rows'])
        check(table+' arrival reconciliation',con.execute(f'select sum(eligible_arrivals-on_time_flights-delayed_flights) from {table}').fetchone()[0],0)
    check('airport key uniqueness',con.execute('select count(*)-count(distinct airport_key) from dim_airport').fetchone()[0],0)
    check('airport code uniqueness',con.execute('select count(*)-count(distinct airport_code) from dim_airport').fetchone()[0],0)
    check('coordinate bounds',con.execute('select count(*) from dim_airport where latitude not between -90 and 90 or longitude not between -180 and 180').fetchone()[0],0)
    check('Phoenix coordinate anchor',con.execute("select count(*) from dim_airport where airport_code='PHX' and abs(latitude-33.435302)<0.01 and abs(longitude+112.005905)<0.01").fetchone()[0],1)
    check('airline key uniqueness',con.execute('select count(*)-count(distinct airline_key) from dim_airline').fetchone()[0],0)
    check('peer groups have competitors',con.execute('select count(*) from carrier_peers where carrier_count<2 or peer_n<=0').fetchone()[0],0)
    profile['tableau_rows']=con.execute('select count(*) from tableau_operations').fetchone()[0]
    if profile['tableau_rows']>=14000000:raise ValueError('Extract is too large; refine analytical grain')
    profile['unmapped_airports']=con.execute('select airport_code from dim_airport where latitude is null or longitude is null').fetchdf()['airport_code'].tolist()
    profile['built_at']=datetime.now(timezone.utc).isoformat();profile['through']=args.through
    dump(PROCESSED/'quality_profile.json',profile);dump(ROOT/'docs/evidence/validation.json',tests)
    if not all(t['passed'] for t in tests):raise ValueError('Validation failed: inspect docs/evidence/validation.json')
    for table in [*specs,'dim_airport','dim_airline','matched_dayparts','carrier_peers','tableau_operations']:
        con.execute(f"COPY {table} TO '{EXPORT/table}.csv' (HEADER,DELIMITER ',')")
    excel={table:con.execute(f'SELECT * FROM {table}').fetchdf().to_dict('records') for table in specs if table!='airport_hourly'}
    excel['airports']=con.execute('SELECT * FROM dim_airport ORDER BY airport_code').fetchdf().to_dict('records')
    excel['carriers']=con.execute('SELECT * FROM dim_airline ORDER BY carrier_name').fetchdf().to_dict('records')
    excel['matched']=con.execute('SELECT year,sum(common_weight*morning_rate)/sum(common_weight) AS morning_rate,sum(common_weight*evening_rate)/sum(common_weight) AS evening_rate,count(*) AS matched_cells,sum(morning_n+evening_n) AS represented_arrivals FROM matched_dayparts GROUP BY 1 ORDER BY 1').fetchdf().to_dict('records')
    excel['peers']=con.execute('SELECT year,carrier_name,sum(n) AS eligible_arrivals,sum(delayed)*1.0/sum(n) AS delay_rate,sum(n*peer_rate)/sum(n) AS peer_rate,count(*) AS compared_cells FROM carrier_peers p LEFT JOIN dim_airline c USING(airline_key) GROUP BY 1,2 ORDER BY 1,2').fetchdf().to_dict('records')
    excel['profile']=profile;excel['tests']=tests
    # JSON uses null for missing values; no NaN tokens enter the workbook builder.
    text=json.dumps(excel,default=str).replace('NaN','null')
    (EXPORT/'excel_data.json').write_text(text)
    con.close();print(json.dumps(profile,default=str,indent=2),flush=True)

if __name__=='__main__':main()
