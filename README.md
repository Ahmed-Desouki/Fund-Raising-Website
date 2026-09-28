# Fundraiser: Crowdfunding Platform for Egypt

ITI Django final project (team 2). People can start fundraising campaigns for charity and community projects, and others can donate, rate, and comment. A help chatbot answers in Arabic or English.

## Features

**Accounts** (`main` app)
- Register with name, email, password, Egyptian mobile number and profile picture
- Email activation link, valid for 24 hours. You can't log in before activating
- Log in with email and password
- Forgot password: reset link by email, valid for 24 hours and single-use
- Profile: edit everything except email, with optional birthdate, Facebook profile and country. Shows your campaigns and donations
- Delete account: confirmation step plus your password

**Campaigns** (`projects` app)
- Create a campaign: title, details, category, multiple pictures, target in EGP, tags, start/end time
- Donate (preset or custom amount); see donors, days left and recent donations
- Comments with replies; report campaigns and comments
- Rate 1–5; the campaign page shows the average rating
- Owner can cancel while donations are under 25% of the target
- Picture slider, 4 similar campaigns by tags, share buttons

**Home page**
- Slider of the 5 highest-rated running campaigns
- Latest 5 campaigns, latest 5 featured campaigns (chosen by the admin), categories
- Search by title or tag

**Help chatbot** (`chatbot` app)
- Chat button on every page, with an **عربي / English** switch
- Explains how the site works and recommends live campaigns from the database
- Runs on the Google Gemini free tier

## Tech stack

Python 3 · Django · SQLite (default) or PostgreSQL · Google Gemini API · plain HTML/CSS/JS

## Run it locally

```bash
git clone https://github.com/Ahmed-Desouki/Fund-Raising-Website.git
cd Fund-Raising-Website

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

Create a file called `.env` next to `manage.py` (copy `.env.example`):

```
SECRET_KEY=any-long-random-string
DEBUG=True
```

Then:

```bash
python manage.py migrate
python manage.py seed_demo        # optional: demo users and campaigns
python manage.py createsuperuser  # optional: for /admin
python manage.py runserver
```

Open http://127.0.0.1:8000

The demo accounts' password is `DEMO_PASSWORD` in `projects/management/commands/seed_demo.py`.

### Activation emails

By default, emails are printed in the terminal where `runserver` is running. Copy the activation link from there.

To really send them through Gmail, add to `.env`:

```
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=your 16-letter App Password
```

Create the App Password at https://myaccount.google.com/apppasswords (needs 2-Step Verification). It must belong to the same Gmail account as `EMAIL_HOST_USER`. Never use your normal Gmail password.

## Optional settings (`.env`)

| Variable | What it does |
|---|---|
| `GEMINI_API_KEY` | Turns on the chatbot. Free key: https://aistudio.google.com/apikey. Without it the bot says it's unavailable. |
| `GEMINI_MODELS` | Comma-separated models tried in order. Default: `gemini-3.8-flash,gemini-flash-latest,gemini-flash-lite-latest` |
| `DATABASE_URL` | Use PostgreSQL instead of SQLite, e.g. `postgresql://user:password@localhost:5432/fundraiser` |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Send real emails through Gmail (see above) |
| `ALLOWED_HOSTS` | Comma-separated hosts, default `127.0.0.1,localhost` |

Never commit `.env`; it's in `.gitignore`.

## Admin panel

Go to http://127.0.0.1:8000/admin with a superuser to:
- add categories (7 are created by the first `migrate`)
- tick **Featured** on campaigns to show them on the home page
- review reported campaigns and comments

## Project structure

```
myproject/   settings and root URLs
main/        registration, activation, login, profile
projects/    campaigns, donations, comments, ratings, reports, home page, search
chatbot/     help chatbot (Gemini) and its chat widget
docs/ERD.md  database diagram
```

## Database

See the diagram in [docs/ERD.md](docs/ERD.md).

## Tests

```bash
python manage.py test
```

## Team workflow

- Work on a branch (`git checkout -b feature/your-thing`) and open a Pull Request into `main`
- Pull before you start: `git pull`
- After pulling, run `pip install -r requirements.txt` and `python manage.py migrate`
