# Database Entity Relationship Diagram

The Mermaid block below renders the booking system entities and their relationships. Open this file in VS Code with the Mermaid Chart extension to visualize the ER diagram.

```mermaid
erDiagram
    HOTEL ||--o{ ROOM : "has many"
    USER ||--o{ BOOKING : "makes"
    ROOM ||--o{ BOOKING : "is booked in"

    HOTEL {
        uuid id PK
        string name
        string phone_number
        string email
        string address
        string city
        string country
        timestamp created_at
        timestamp last_modified_at
    }

    ROOM {
        uuid id PK
        uuid hotel_id FK
        string number
        string size
        int price
    }

    USER {
        uuid id PK
        string name
        string surname
        string email
        string phone_number
    }

    BOOKING {
        uuid id PK
        uuid guest_id FK
        uuid room_id FK
        date start_date
        date end_date
        int duration
        string status
        timestamp created_at
        timestamp last_modified_at
    }
```
