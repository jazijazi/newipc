from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import (
    Gharardad as LegacyGharardad,
)
from contracts.models.models import (
    Contract as NewContract,
    ContractDomin as NewContractDomin,
)
from common.models import Company as NewCompany


class Command(BaseCommand):
    help = 'Migrate Contract (Gharardad) data from legacy database'

    # Map legacy department names to new DEPARTMENT_CHOICES codes
    DEPARTMENT_MAPPING = {
        "خدمات مشاوره ایی": "1",
        "حفاری": "2",
        "ژئوفیزیک": "3",
        "چاه پیمایی": "4",
        "آزمایشگاه": "5",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run migration without committing changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no changes will be saved'))
        
        legacy_contracts = LegacyGharardad.objects.using('legacy').all()
        total_count = legacy_contracts.count()
        
        self.stdout.write(f'Found {total_count} contracts in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for legacy_contract in legacy_contracts:
            try:
                # Check if already migrated by oldid
                existing = NewContract.objects.filter(oldid=legacy_contract.pk).exists()
                if existing:
                    self.stdout.write(self.style.WARNING(f'Skipping: {legacy_contract.titlegh} - already migrated'))
                    skipped_count += 1
                    continue
                
                # Find matching ContractDomin
                new_domain = None
                if legacy_contract.dtyp:
                    new_domain = NewContractDomin.objects.filter(
                        title=legacy_contract.dtyp.gharartype,
                        code=legacy_contract.dtyp.codetype
                    ).first()
                    
                    if not new_domain:
                        self.stdout.write(
                            self.style.WARNING(f'Domain not found for {legacy_contract.titlegh}')
                        )
                
                # Map department
                new_department = None
                if legacy_contract.department:
                    new_department = self.DEPARTMENT_MAPPING.get(legacy_contract.department.strip())
                    if not new_department:
                        self.stdout.write(
                            self.style.WARNING(f'Department "{legacy_contract.department}" not found in mapping for {legacy_contract.titlegh}')
                        )
                
                if not dry_run:
                    with transaction.atomic():
                        # Create contract
                        new_contract = NewContract.objects.create(
                            oldid=legacy_contract.pk,
                            title=legacy_contract.titlegh,
                            dtyp=new_domain,
                            number=legacy_contract.ghararNo,
                            start_date=legacy_contract.startprj,
                            end_date=legacy_contract.endprj,
                            progress=legacy_contract.pishraft,
                            is_completed=legacy_contract.khatemeh,
                            department=new_department,
                            mablagh=legacy_contract.mablagh,
                            elhaghye=legacy_contract.elhaghye,
                            mablaghe_elhaghye=legacy_contract.mablaghe_elhaghye,
                            tarikh_elhaghye=legacy_contract.tarikh_elhaghye
                        )
                        
                        # Add M2M relationships for companies
                        legacy_companies = legacy_contract.sherkatejraei.all()
                        for legacy_company in legacy_companies:
                            # Find matching company by name, code, and typ
                            new_company = NewCompany.objects.filter(
                                name=legacy_company.name,
                                code=legacy_company.code,
                                typ=legacy_company.typ
                            ).first()
                            
                            if new_company:
                                new_contract.company.add(new_company)
                            else:
                                self.stdout.write(
                                    self.style.WARNING(f'Company not found: {legacy_company.name} for contract {legacy_contract.titlegh}')
                                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Migrated: {legacy_contract.titlegh}')
                )
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating {legacy_contract.titlegh}: {str(e)}')
                )
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total contracts in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))