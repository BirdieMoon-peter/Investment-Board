from sqlmodel import Session, select

from app.db.models import CompanyProfile


class CompanyProfileRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert(self, profile: CompanyProfile, *, commit: bool = True) -> CompanyProfile:
        existing = self.get_by_security_id(profile.security_id)

        if existing is None:
            persisted = CompanyProfile(
                security_id=profile.security_id,
                full_name=profile.full_name,
                english_name=profile.english_name,
                registered_capital=profile.registered_capital,
                establishment_date=profile.establishment_date,
                website=profile.website,
                main_business=profile.main_business,
                employees=profile.employees,
            )
            self.session.add(persisted)
        else:
            existing.full_name = profile.full_name
            existing.english_name = profile.english_name
            existing.registered_capital = profile.registered_capital
            existing.establishment_date = profile.establishment_date
            existing.website = profile.website
            existing.main_business = profile.main_business
            existing.employees = profile.employees
            persisted = existing

        if commit:
            self.session.commit()
        else:
            self.session.flush()

        self.session.refresh(persisted)
        return persisted

    def get_by_security_id(self, security_id: int) -> CompanyProfile | None:
        statement = select(CompanyProfile).where(CompanyProfile.security_id == security_id)
        return self.session.exec(statement).first()
