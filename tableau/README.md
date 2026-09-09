# Open or edit the Tableau dashboard

**[Explore the published dashboard](https://public.tableau.com/app/profile/shashank.pabitwar/viz/WHENAMERICARUNSLATE/WhenAmericaRunsLate)**

**[Download When_America_Runs_Late.twbx](https://github.com/Shashankpabitwar123/us-airline-operations-delay-analytics/raw/refs/heads/main/tableau/When_America_Runs_Late.twbx)**

The file in this folder was downloaded from the finished Tableau Public publication on September 9, 2026. It contains the workbook, Hyper extract and graphics, so no external database connection is needed to view this saved snapshot.

## Use it

1. Download the `.twbx` file, then open it in a compatible Tableau Desktop or Tableau Desktop Public Edition installation. Use a current version if an older installation reports a version mismatch.
2. Open **When America Runs Late**. Choose year, months, departure airport and airline at the top. Apply the month selection when prompted.
3. Hover over route lines for details. Use **Reset filters** to return to the default selection and **How to read** for definitions.

The default view is January–June 2026, all departure airports and all airlines. Historical data covers January 2023–June 2026. The map displays up to 150 busy directional routes, rather than every route at once.

## Edit it

The package contains **47 worksheets** and the dashboard. Charts, text and floating objects can be edited in Tableau; select an object and use its layout settings to reposition or resize it. Some decorative graphics are grouped in an SVG background, so their individual shapes are not separate Tableau objects. Help icons are packaged SVG assets.

Save a separate copy before experimenting. For visual changes, preserve the data connections, calculation references and action definitions. The included package is the published version; hand-editing its XML can introduce errors that a simple XML syntax check will not detect.

## Read the colors

| Route line | Share of eligible arrivals that were late |
|---|---|
| Blue | Under 15% |
| Orange | 15% to under 30% |
| Red | 30% or more |
| Grey | Fewer than 100 recorded eligible arrivals; interpret cautiously |

The legend follows the categories present in the filtered view. Curves are schematic airport connections. Alaska, Hawaii and island insets use separate scales.

[Dashboard preview](../docs/images/tableau-dashboard.png) · [Build story](../docs/project_story.md) · [Verification and limitations](../docs/release_status.md)
