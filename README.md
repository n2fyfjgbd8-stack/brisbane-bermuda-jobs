# Brisbane & Bermuda IT Jobs

Free public job-search dashboard for permanent IT infrastructure roles in Brisbane and Bermuda.

## Publish on GitHub Pages
1. Open **Settings → Pages** in this repository.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Set the branch to **main** and the folder to **/docs**, then click **Save**.
4. Your public site should be at https://n2fyfjgbd8-stack.github.io/brisbane-bermuda-jobs/ after GitHub finishes deploying it.

## Job-feed refresh
The [Refresh job listings](../../actions/workflows/refresh.yml) GitHub Actions workflow is configured for 7 and 37 minutes past the hour (targeting twice an hour). GitHub may delay or skip scheduled jobs.
- Open the **Actions** tab, choose **Refresh job listings**, then **Run workflow** for an initial check.
- The script checks public Arbeitnow, Dev Global Jobs (Australia/Bermuda country searches), and OnJob feeds. It accepts only listings explicitly located in Brisbane/Queensland or Bermuda. Free feeds can still contain expired or inaccurately labeled jobs; verify each employer link. The site credits source providers.
- Optional: add free Adzuna credentials as repository Actions secrets **ADZUNA_APP_ID** and **ADZUNA_APP_KEY**. Without these, Brisbane coverage may be very limited. The Dev Global Jobs Bermuda query is configured, but this does not guarantee Bermuda listings. Brisbane coverage can be improved with Adzuna credentials.
- The site shows the 11 original leads **as historical / unverified**, separately from any feed listings. It does not assert these leads are open.
- The workflow commits docs/jobs.json when changed. If pushing fails, check **Settings → Actions → General → Workflow permissions** for read/write access.

## Limitations
- Live-feed records are not verified for permanent contracts, sponsorship or ongoing vacancy status.
- No paid API, guaranteed coverage, or 30-minute service-level agreement.
- GitHub Pages is public. Do not publish personal job application details.
- A zero-record live feed is possible and is shown honestly. Sources may fail, paginate or return no matching vacancies.\n- Data credits: Dev Global Jobs https://devglobaljobs.com, OnJob https://onjob.io, and Arbeitnow.\n- After source changes, run the workflow manually from GitHub Actions to see the results immediately.
