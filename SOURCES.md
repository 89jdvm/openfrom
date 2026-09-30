# Sources

openfrom lists remote jobs from public job boards and from employers' own career pages. Every job links back to the page that published it, and the site credits the source by name. Only a job's title, employer, location, dates, stated pay, labels and a summary of at most 200 characters are published; the full ad text is read during the nightly build and then discarded.

The rule for including a source: list every public board whose terms or robots.txt allow it, with credit and a link back, and drop any board whose terms or robots.txt forbid it. Where a source publishes an API or feed and invites reuse, that invitation is read as the permission, even when its website carries generic "personal use only" wording. The terms below were read on 30 September 2026.

## Listed

| Source | What is read | Terms or robots.txt | What the terms ask |
|---|---|---|---|
| [Himalayas](https://himalayas.app) | Public jobs API, newest first | [himalayas.app/api](https://himalayas.app/api) | "please link back to the URL found on Himalayas AND mention Himalayas as the original source". Jobs link to the Himalayas page. |
| [Remote OK](https://remoteok.com) | Public jobs API | Legal notice in the [API reply](https://remoteok.com/api) | "Please link back (with follow, and without nofollow!) to the URL on Remote OK and mention Remote OK as a source". Jobs link to the Remote OK page. |
| [Jobicy](https://jobicy.com) | Public jobs API | [jobicy.com/jobs-rss-feed](https://jobicy.com/jobs-rss-feed) | "Keep Jobicy as the original source and preserve the canonical Jobicy job URL when displaying listings." Polled at most once a day. |
| [We Work Remotely](https://weworkremotely.com) | RSS feeds | [weworkremotely.com/remote-job-rss-feed](https://weworkremotely.com/remote-job-rss-feed) | "Anyone can use the feed, all we ask is that you attribute the links back to We Work Remotely." |
| [Real Work From Anywhere](https://www.realworkfromanywhere.com) | RSS feeds | [realworkfromanywhere.com/rss-feeds](https://www.realworkfromanywhere.com/rss-feeds) | "RSS feeds are completely free and don't require any account creation." No reuse terms stated. |
| [Arbeitnow](https://www.arbeitnow.com) | Free job-board API (remote jobs only) | [arbeitnow.com/blog/job-board-api](https://www.arbeitnow.com/blog/job-board-api) | The API is offered free with no key. The website's general terms carry a personal-use licence; the API page invites developers to use it. |
| [Working Nomads](https://www.workingnomads.com) | The site's public search index | [robots.txt](https://www.workingnomads.com/robots.txt) allows all paths | No terms page found. Read gently: pages of 500, three seconds apart. |
| [Workable](https://jobs.workable.com) | Public job board API, remote jobs of the last 30 days | [jobs.workable.com/terms](https://jobs.workable.com/terms); robots.txt allows the API | No clause on automated access or reuse. |
| Greenhouse, Lever, Ashby and Recruitee boards | Employers' own public job-board APIs (92 employers) | [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html) | "Job Board data is publicly available, so authentication is not required for any GET endpoints." These APIs exist so employers can show their openings anywhere. Jobs link to the employer's page. |
| [NGO Job Board](https://ngojobboard.org) | Public RSS feed | [Terms](https://ngojobboard.org/terms-and-conditions/); robots.txt allows the feed | No clause on reading or linking to the feed. |
| [PCDN](https://pcdn.global) | Public RSS feed | [Terms](https://pcdn.global/terms-of-service/); robots.txt allows all | No clause on reading or linking to the feed. |

## Left out

| Source | Reason |
|---|---|
| [4dayweek.io](https://4dayweek.io) | Its [terms](https://4dayweek.io/terms) say API results may not be used to "build, train or populate a competing job board or a substantially similar database". Also excluded from training data. |
| [Get on Board](https://www.getonbrd.com) | Its [terms](https://www.getonbrd.com/pages/get-on-board-terms-and-conditions-agreement) forbid using the platform "to train models" and to "reproduce, transfer, publish, distribute... or display" its content. Also excluded from training data. |
| [ReliefWeb](https://reliefweb.int) | Its [terms](https://reliefweb.int/terms-conditions) allow downloads "for the User's personal, non-commercial use, without any right to resell or redistribute them or to compile or create derivative works". Its API needs a registered app name, and this project uses no sign-ups. |
| [UN Careers](https://careers.un.org) | The [United Nations terms of use](https://www.un.org/en/about-us/terms-of-use) carry the same personal-use wording as ReliefWeb. |
| [SmartRecruiters](https://www.smartrecruiters.com) | The robots.txt on its API host disallows every path for all crawlers except LinkedIn's. |
| [Jobgether](https://jobgether.com) | Its robots.txt disallows every URL with a query string, which its jobs API needs. Its separate AI feed is described as serving assistants that answer one person's search. |
| [The Green Recruitment Company](https://www.greenrecruitmentcompany.com) | Its feed held five jobs on the night of the first build, none of them remote. |

## Training data

The labels (role family, industry, seniority, contract type, employer type) are learned from an earlier labelling study of 56,424 postings. That data trains the models and is never listed. Postings from sources whose terms forbid training (4dayweek, Get on Board) and sources that are not remote job boards were removed before training.
