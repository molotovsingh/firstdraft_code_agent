import uuid
from shared.db.session import SessionLocal
from shared.db import models


def main():
    db = SessionLocal()
    try:
        # Create a default tenant and users if not exist
        tenant_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        tenant = db.get(models.Tenant, tenant_id)
        if tenant is None:
            tenant = models.Tenant(id=tenant_id, name="Dev Tenant")
            db.add(tenant)
            db.commit()

        user1 = db.query(models.User).filter_by(tenant_id=tenant.id, username="amit").first()
        if user1 is None:
            user1 = models.User(tenant_id=tenant.id, username="amit", display_name="Amit")
            db.add(user1)
        user2 = db.query(models.User).filter_by(tenant_id=tenant.id, username="claude").first()
        if user2 is None:
            user2 = models.User(tenant_id=tenant.id, username="claude", display_name="Claude")
            db.add(user2)
        db.commit()
        print("Bootstrap complete. Users:")
        for u in db.query(models.User).filter_by(tenant_id=tenant.id).all():
            print(f"- id={u.id} username={u.username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

