Project Journal

Session 1: Data Source and Import Problems

- I started by downloading the accredited Skills Development Providers dataset from the QCTO database as a CSV file.
- The first major issue appeared when I loaded the CSV into Excel. Some values spilled into the wrong columns, which made the dataset unreliable and difficult to work with.
- I first tried workarounds such as duplicating the source into Airtable and using CSV Getter to convert it into a cleaner Google Sheets version.
- That route helped me understand the source structure better, but it later introduced its own problems.
- After more testing, I found that importing the original CSV directly into Google Sheets was the simplest and most reliable method because it preserved the structure without the same Excel import problems.

Session 2: First Audit and Early Column Planning

- Once the structure was more stable, I reviewed the columns and decided what looked useful for the dashboard idea at that stage.
- In the early version, I focused mainly on provider name, qualification title, NQF level, quality partner, status, location, and contact details.
- I dropped several administrative or backend fields that did not seem necessary for the first version.
- I also realised very early that I would need some kind of career-path field later.
- One of the main goals of the project was to allow a user to choose a role and then see matching qualifications, or choose a qualification and then see possible career paths.
- At that stage I did not yet know the best structure for it, but I noted it as something important for later.

Session 3: Manual Cleaning in Google Sheets and the First Reset

- At the beginning of cleaning, Excel kept crashing while I was filtering and editing the dataset, so I moved to Google Sheets for the heavy manual work.
- One of the biggest early issues was that the Province column contained city and town names, while some of those values really belonged in the Town-City column.
- I filtered out the valid province names, copied the incorrect town and city values into the correct column, and then fixed the Province values separately.
- For some of the repetitive replacements, I used AI to speed up the process instead of typing every correction manually.
- This phase helped me clean obvious structural problems, but it also showed that the first workflow was not stable enough for the full project.
- Because of that, I later reset parts of the process and moved toward script-based cleaning.

Session 4: Moving from Manual Cleaning to Scripted Cleaning

- After the first cleanup stage, I started using Python to clean the dataset more consistently across the full 49,000+ rows.
- This was necessary because the file was too large and repetitive for manual work alone.
- The first scripts handled things like removing empty columns, trimming spaces, standardising dates, normalising SETA names, cleaning emails, fixing phone numbers, and creating helper columns for the dashboard.
- This was the point where the project changed from being just a spreadsheet-cleaning task into a proper data preparation workflow.
- AI helped a lot here with generating and refining scripts, but I still had to inspect the outputs carefully because some fixes that worked on samples did not always hold up on the full file.

Session 5: Full-File Inspection and Fixing Hidden Issues

- Once I started checking the full cleaned outputs instead of only trusting sample results, I found more problems.
- Some phone numbers were technically fixed in the script but were still being damaged later when saved in the wrong format.
- Some qualification titles still had formatting inconsistencies.
- Some contact person values were actually email addresses.
- Some town values were still street names or address fragments.
- I also had to revisit how "NATED" was being treated, because it appeared under the quality partner field even though it is not actually a SETA.
- At this stage I stopped relying blindly on earlier fixes and made it a rule to inspect the real output first, then compare it against what the AI-assisted script claimed it had fixed.

Session 6: Final Standardisation and Helper Columns

- The later cleaning versions were focused on making the data dashboard-ready.
- By this point the project had moved beyond the first list of keep and remove columns.
- Some fields I originally thought I would not need, like Credits and the accreditation dates, were brought back because they later became useful for calculations, expiry tracking, or context.
- I also added several helper columns to support analysis and visuals.
- These included fields such as Days Until Expiry, Has Contact Email, Qualification Category, Partner Type, SETA, Is Old Trade, and review flags.
- Later I also cleaned phone numbers into a consistent South African format and converted them to +27 formatting for presentation.
- Town and city values were reviewed more deeply, including misspellings and official naming issues, and a town-review step was created to make that process more transparent.

Session 7: Reframing the NATED Issue

- One important research task during cleaning was understanding what "NATED" meant in the dataset.
- At first it looked like it might need to be treated as a SETA-related category, but after further checking I confirmed that NATED is part of the Report 190/191 qualification framework and not a SETA itself.
- That meant I should not force it into the SETA field as if it were one of the actual funding bodies.
- Instead, I kept it separate through the partner classification logic.
- This was an important step because it made the dashboard more accurate and stopped me from misrepresenting the source data.

Session 8: Career-Path Structure and Moving Beyond One Extra Column

- The original idea was to add one new career column to the main data, but that became too limited once I thought about how the filtering needed to work.
- A single qualification can link to several careers, and one career can link to several qualifications.
- Because of that, I shifted away from a simple comma-separated column and built a separate structure for career mapping.
- The final model used a Qualification Master table, a Qualification-Career Map table, a Career List table, and a linked main SDP table.
- AI helped generate the first pass of the mapping logic and later helped process flagged rows, but there was still manual review involved to make the mappings more realistic.
- This ended up being one of the most important improvements in the whole project because it made the career explorer feature possible.

Session 9: Building the Dashboard Model

- After cleaning the main dataset, I moved into model design.
- I created a qualification key so that the main table could link properly to the qualification and career mapping tables.
- This stage also involved creating supporting columns such as Suggested Career Family, Suggested Primary Career, Suggested Careers, confidence flags, and contact helper fields.
- I later polished the workbook into a model file that was safer to use in Excel and Power BI than repeated CSV imports.
- This was important because import errors had already caused problems earlier in the project, so keeping the final version in Excel format reduced that risk.

Session 10: Dashboard Planning, Mockups, and Choosing the Right Output

- For the dashboard design itself, I explored both Power BI and HTML mockups.
- The Power BI dashboard became the practical, compact version meant for filtering providers, qualifications, contacts, and geographic distribution.
- The HTML side became the place where I could think more freely about more complex layouts and the full career explorer logic without being limited by space on a single Power BI page.
- The design direction settled on using Power BI for the main dashboard and the eventual HTML or GitHub Pages version for the richer career-to-qualification-to-provider experience.
- This matched the earlier thinking that the career feature would likely work better as a companion web experience rather than being forced entirely into one Power BI page.

Session 11: Power BI Build and Refinement

- When I began building the Power BI dashboard, the main challenge was not the data anymore but space.
- I wanted to include cards, map visuals, SETA and quality partner visuals, NQF level distribution, provider information, contact details, and the career idea without overcrowding the page.
- I refined the layout several times and learned that some features that looked good in a mockup needed to be simplified in Power BI.
- I also created DAX measures for cards such as accreditation records, unique organisations, active accreditations, and records with contact email.
- I adjusted labels so that metrics were clearer. For example, I used "Accreditation records" instead of making it sound like there were 48,000 different providers.
- By the end of this stage, the dashboard was already strong enough to function as a portfolio piece.

Session 12: Final Career Mapping Review and Workbook Polish

- After the model tables were created, there were still rows in the career mapping outputs marked for review.
- AI was used again here to help go through those flagged rows, suggest better mappings, and replace weak placeholders with more realistic career paths.
- Qualification categories were also improved further, and rows that had stayed too general were made more specific where possible.
- The workbook was then polished so that it would open cleanly in Excel and be easier to use in Power BI.
- Formatting was improved across sheets, helper fields were cleaned up, and the career mapping structure became much more complete.

Session 13: Final Dashboard Completion

- The final dashboard includes the core things I originally wanted, but in a cleaner and more realistic structure than I first imagined.
- The final Power BI version focuses on overview and filtering.
- It shows accreditation records, unique organisations, active accreditations, quality partner distribution, NQF level distribution, provider location, and contact details.
- It also includes a provider table with contact details and career-related information.
- The HTML side remains useful for design ideas and for thinking about the more advanced career explorer experience.
- At this stage, the dashboard is no longer just an idea. It is a completed project with cleaned data, linked model tables, helper columns, career logic, and a working dashboard layout.

Current Project Structure

- The project is no longer based on the first reduced list of columns.
- The final version includes the core provider, qualification, location, status, and contact fields.
- It also includes helper columns for expiry, contactability, category, partner classification, and career-path logic.
- The project now uses linked supporting tables for qualifications and careers instead of trying to force everything into one flat dataset.

Main Tools Used

- Google Sheets for early import and manual cleaning
- Excel for workbook-based model files
- Python for large-scale cleaning and helper-column generation
- Power BI for the dashboard
- AI assistance for scripting, repetitive fixes, mapping suggestions, design mockups, and documentation support

Final Reflection

- This project changed a lot from the way I first imagined it.
- It started as a dashboard idea built from a messy public dataset, but it became a much bigger exercise in data auditing, cleaning, standardisation, data modelling, career-path mapping, and dashboard design.
- I used AI throughout the project for large repetitive tasks such as code generation, mapping suggestions, text cleanup, design mockups, and troubleshooting.
- At the same time, I still had to inspect the results manually, reset parts of the workflow when they were not reliable, and make judgement calls about what to keep, what to remove, and what needed a more accurate structure.
- That balance between automation and manual review ended up being one of the most important lessons from the whole project.

