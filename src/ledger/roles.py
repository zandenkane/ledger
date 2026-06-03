"""Role constants and seeding logic for the roles reference table."""

KNOWN_ROLES: list[str] = [
    "producer",
    "director",
    "composer",
    "engineer",
    "performer",
    "editor",
    "cinematographer",
    "mixer",
    "writer",
    "artist",
    "designer",
    "animator",
    "other",
]


def seed_roles(conn) -> None:
    """Insert known roles into the roles table if they don't already exist."""
    cursor = conn.cursor()
    for role in KNOWN_ROLES:
        cursor.execute(
            "INSERT OR IGNORE INTO roles (name) VALUES (?)",
            (role,),
        )
    conn.commit()
