# Database ERD

GitHub renders the diagram below automatically. Table names are the ones Django creates (`<app>_<model>`); `auth_user` is Django's built-in user table.

```mermaid
erDiagram
    auth_user ||--|| main_profile : "has"
    auth_user ||--o{ projects_project : "owns"
    auth_user ||--o{ projects_donation : "makes"
    auth_user ||--o{ projects_comment : "writes"
    auth_user ||--o{ projects_rating : "gives"
    auth_user ||--o{ projects_projectreport : "files"
    auth_user ||--o{ projects_commentreport : "files"

    projects_category ||--o{ projects_project : "groups"
    projects_project }o--o{ projects_tag : "tagged with"
    projects_project ||--o{ projects_projectimage : "has"
    projects_project ||--o{ projects_donation : "receives"
    projects_project ||--o{ projects_comment : "has"
    projects_project ||--o{ projects_rating : "has"
    projects_project ||--o{ projects_projectreport : "reported in"

    projects_comment ||--o{ projects_comment : "replies"
    projects_comment ||--o{ projects_commentreport : "reported in"

    auth_user {
        int id PK
        string username "same as email"
        string email "unique, checked at registration"
        string password "hashed"
        string first_name
        string last_name
        bool is_active "false until email activation"
        datetime date_joined
    }

    main_profile {
        int id PK
        int user_id FK, UK
        string mobile_number "Egyptian: 010/011/012/015 + 8 digits"
        string profile_picture "optional image path"
        date birthdate "optional"
        string facebook_profile "optional URL"
        string country "optional"
    }

    projects_category {
        int id PK
        string name UK
    }

    projects_tag {
        int id PK
        string name UK
    }

    projects_project {
        int id PK
        int owner_id FK
        int category_id FK
        string title
        text details
        decimal total_target "EGP"
        datetime start_time
        datetime end_time
        bool is_featured "chosen by admin"
        bool is_cancelled
        datetime created_at
    }

    projects_projectimage {
        int id PK
        int project_id FK
        string image "image path"
    }

    projects_donation {
        int id PK
        int project_id FK
        int user_id FK
        decimal amount "EGP, min 1"
        datetime created_at
    }

    projects_comment {
        int id PK
        int project_id FK
        int user_id FK
        int parent_id FK "null for top-level comments"
        text content
        datetime created_at
    }

    projects_rating {
        int id PK
        int project_id FK
        int user_id FK
        int value "1 to 5, one per user per project"
    }

    projects_projectreport {
        int id PK
        int project_id FK
        int user_id FK
        text reason
        datetime created_at
    }

    projects_commentreport {
        int id PK
        int comment_id FK
        int user_id FK
        text reason
        datetime created_at
    }
```

`projects_project` and `projects_tag` are linked through Django's join table `projects_project_tags` (`project_id`, `tag_id`).

## Rules enforced by the code

| Rule | Where |
|---|---|
| A user can't log in until they click the activation link (valid 24 hours) | `main/views.py`, `main/tokens.py` |
| Mobile number must be Egyptian | `main/forms.py` |
| One rating per user per project (rating again updates it) | `Rating` unique constraint, `projects/views.py` |
| Owner can cancel only while donations are under 25% of the target | `Project.can_be_cancelled` |
| Donations only while the campaign is running and not cancelled | `Project.is_running`, `projects/views.py` |
| End time must be after start time | `projects/forms.py` |
| Deleting a user deletes their profile, projects, donations, comments, ratings and reports | `on_delete=CASCADE` |
| A category that still has projects can't be deleted | `on_delete=PROTECT` |

The chatbot stores nothing in the database; its per-visitor rate limit lives in the session.
