#!/usr/bin/env python3
"""Independent evidence tables and an executed notebook for the Flightpath release."""
from pathlib import Path
import json, math
import duckdb, nbformat
from nbclient import NotebookClient
ROOT=Path(__file__).resolve().parents[1]; E=ROOT/'docs/evidence'; E.mkdir(parents=True,exist_ok=True)
con=duckdb.connect(str(ROOT/'data/processed/flightpath.duckdb'),read_only=True)
queries={
 'half_year_comparison':"SELECT year,sum(scheduled_flights) AS scheduled_flights,sum(eligible_arrivals) AS eligible_arrivals,sum(on_time_flights)*1.0/sum(eligible_arrivals) AS on_time_rate,sum(cancelled_flights)*1.0/sum(scheduled_flights) AS cancellation_rate FROM monthly WHERE month<=6 GROUP BY 1 ORDER BY 1",
 'full_year_comparison':"SELECT year,sum(scheduled_flights) AS scheduled_flights,sum(eligible_arrivals) AS eligible_arrivals,sum(on_time_flights)*1.0/sum(eligible_arrivals) AS on_time_rate FROM monthly WHERE year<=2025 GROUP BY 1 ORDER BY 1",
 'matched_dayparts':"SELECT year,sum(common_weight*morning_rate)/sum(common_weight) AS morning_rate,sum(common_weight*evening_rate)/sum(common_weight) AS evening_rate,sum(common_weight*gap)/sum(common_weight) AS gap,count(*) AS matched_cells,sum(morning_n+evening_n) AS represented_arrivals FROM matched_dayparts WHERE month<=6 GROUP BY 1 ORDER BY 1",
 'matched_sensitivity':"SELECT threshold,year,count(*) AS matched_cells,sum(common_weight*gap)/sum(common_weight) AS gap FROM matched_dayparts CROSS JOIN (VALUES (30),(60),(100)) limits(threshold) WHERE month<=6 AND morning_n>=threshold AND evening_n>=threshold GROUP BY 1,2 ORDER BY 1,2",
 'hourly_profile':"SELECT year,departure_hour,sum(scheduled_flights) AS scheduled_flights,sum(eligible_arrivals) AS eligible_arrivals,sum(delayed_flights) AS delayed_flights,sum(delayed_flights)*1.0/sum(eligible_arrivals) AS delay_rate FROM hourly WHERE month<=6 GROUP BY 1,2 ORDER BY 1,2",
 'peer_comparison':"SELECT year,carrier_name,sum(n) AS eligible_arrivals,count(*) AS matched_cells,sum(n*gap)/sum(n) AS difference_from_competitors FROM carrier_peers LEFT JOIN dim_airline USING(airline_key) WHERE month<=6 GROUP BY 1,2 ORDER BY 1,5",
 'observed_dayparts':"SELECT year,departure_period,count(*) AS scheduled_flights,sum(eligible_arrival) AS eligible_arrivals,sum(delayed_flight)*1.0/sum(eligible_arrival) AS delay_rate FROM fact_flights WHERE month<=6 GROUP BY 1,2 ORDER BY 1,2",
}
evidence={}
for name,q in queries.items():
    frame=con.execute(q).fetchdf();frame.to_csv(E/(name+'.csv'),index=False);evidence[name]=frame.to_dict('records')
(E/'findings.json').write_text(json.dumps(evidence,indent=2))
# Flight-level independent reconciliation against presentation grain, stratified by year and month.
check=con.execute('''WITH f AS (SELECT year,month,count(*) AS n,sum(eligible_arrival) AS eligible,sum(delayed_flight) AS delayed FROM fact_flights GROUP BY 1,2),
 t AS (SELECT year,month,sum(scheduled_flights) AS n,sum(eligible_arrivals) AS eligible,sum(delayed_flights) AS delayed FROM tableau_operations GROUP BY 1,2)
 SELECT count(*) FROM f FULL JOIN t USING(year,month) WHERE f.n IS DISTINCT FROM t.n OR f.eligible IS DISTINCT FROM t.eligible OR f.delayed IS DISTINCT FROM t.delayed''').fetchone()[0]
assert check==0, 'Presentation extract differs from flight-level data'
# Boundary audit uses actual records on either side of arrival thresholds.
boundary=con.execute('''SELECT arrival_delay_minutes,count(*) AS flights,min(arrived_on_time) AS min_on_time,max(arrived_on_time) AS max_on_time,min(delayed_flight) AS min_delayed,max(delayed_flight) AS max_delayed,min(severe_delay) AS min_severe,max(severe_delay) AS max_severe FROM fact_flights WHERE eligible_arrival=1 AND arrival_delay_minutes IN(14,15,59,60,119,120) GROUP BY 1 ORDER BY 1''').fetchdf()
for r in boundary.to_dict('records'):
    minutes=r['arrival_delay_minutes'];assert r['min_on_time']==r['max_on_time']==int(minutes<15);assert r['min_delayed']==r['max_delayed']==int(minutes>=15);assert r['min_severe']==r['max_severe']==int(minutes>=60)
boundary.to_csv(E/'threshold_checks.csv',index=False);con.close()
nb=nbformat.v4.new_notebook();nb.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
nb.cells=[nbformat.v4.new_markdown_cell('''# Flightpath: U.S. airline reliability

24,416,952 scheduled flights, January 2023–June 2026. BTS reporting-carrier records.

This notebook reads the same corrected model used by Excel and Tableau. Arrival rates exclude cancelled, diverted and missing-arrival records. Half-year comparisons use January–June in every year. Patterns are descriptive; a matched comparison does not identify a causal effect.'''),nbformat.v4.new_code_cell("from pathlib import Path\nimport duckdb\nroot=Path.cwd().parent if Path.cwd().name=='notebooks' else Path.cwd()\ncon=duckdb.connect(str(root/'data/processed/flightpath.duckdb'),read_only=True)")]
descriptions={
'half_year_comparison':'## Comparable January–June windows\nThe partial 2026 release is compared with the same six months in earlier years.',
'full_year_comparison':'## Complete years\n2026 is intentionally absent from a full-year comparison.',
'matched_dayparts':'## Morning versus evening within comparable operating cells\nCells use the same directional route, reporting carrier and calendar month. At least 30 eligible arrivals are required in each period. Common weights equal the smaller of the morning/evening counts. Coverage is reported; results do not generalize automatically to unmatched cells.',
'matched_sensitivity':'## Sensitivity to sample-size thresholds\nCheck whether the pattern survives stricter minimum counts. All versions use the same common-weight formula.',
'hourly_profile':'## The shape of the departure day\nScheduled origin-local hour is the exposure. The outcome remains arrival delay. Overnight sample sizes can be small.',
'peer_comparison':'## Airlines versus other carriers on the same routes\nOnly route-month cells with at least two carriers and at least 100 eligible arrivals per carrier enter. Competitor rates exclude the focal airline. The gap is weighted by the focal airline’s eligible arrivals. Route mix beyond this restricted sample and other confounding remain.',
'observed_dayparts':'## Unadjusted departure periods\nMorning 06:00–10:59; evening 19:00–23:59. These periods are not equal in duration or traffic.'}
for name,q in queries.items():nb.cells.extend([nbformat.v4.new_markdown_cell(descriptions[name]),nbformat.v4.new_code_cell('con.execute('+repr(q)+').fetchdf()')])
nb.cells.append(nbformat.v4.new_code_cell('con.close()'))
p=ROOT/'notebooks/flightpath_analysis.ipynb';nbformat.write(nb,p)
NotebookClient(nb,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}}).execute();nbformat.write(nb,p)
print('Evidence and executed notebook saved')
