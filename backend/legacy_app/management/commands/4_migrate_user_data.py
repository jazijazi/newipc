from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import IpcUser, IpcRole, SherkatEjraei

from common.models import Company
from accounts.models import User,Roles

class Command(BaseCommand):
    help = 'Migrate users from legacy database to new database'

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
        
        # Get all users from legacy database
        legacy_users = IpcUser.objects.using('legacy').all()
        total_count = legacy_users.count()
        
        self.stdout.write(f'Found {total_count} users in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for legacy_user in legacy_users:
            try:
                # Check if user already exists in new database
                exists = User.objects.filter(username=legacy_user.username).exists()
                
                if exists:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: {legacy_user.username} - already exists')
                    )
                    skipped_count += 1
                    continue
                
                # Find matching role in new database
                new_role = None
                if legacy_user.roles:
                    try:
                        legacy_role = IpcRole.objects.using('legacy').get(id=legacy_user.roles.id)
                        new_role = Roles.objects.filter(title=legacy_role.rolename).first()
                        
                        if not new_role:
                            self.stdout.write(
                                self.style.WARNING(f'Role "{legacy_role.rolename}" not found in new database for user {legacy_user.username}')
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'Error finding role for user {legacy_user.username}: {str(e)}')
                        )
                
                # Find matching company in new database
                new_company = None
                if legacy_user.sherkat:
                    try:
                        legacy_company = SherkatEjraei.objects.using('legacy').get(id=legacy_user.sherkat.id)
                        new_company = Company.objects.filter(name=legacy_company.name).first()
                        
                        if not new_company:
                            self.stdout.write(
                                self.style.WARNING(f'Company "{legacy_company.name}" not found in new database for user {legacy_user.username}')
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'Error finding company for user {legacy_user.username}: {str(e)}')
                        )
                
                if not dry_run:
                    with transaction.atomic():
                        User.objects.create(
                            pk=legacy_user.pk,
                            username=legacy_user.username,
                            first_name=legacy_user.first_name,
                            last_name=legacy_user.last_name,
                            email=legacy_user.email,
                            is_staff=legacy_user.is_staff,
                            is_active=legacy_user.is_active,
                            is_superuser=legacy_user.is_superuser, 
                            date_joined=legacy_user.date_joined,
                            password=legacy_user.password,
                            last_login=legacy_user.last_login,
                            first_name_fa=legacy_user.first_name_fa,
                            last_name_fa=legacy_user.last_name_fa,
                            address=legacy_user.address,
                            phonenumber=legacy_user.phonenumber,
                            codemeli=legacy_user.codemeli,
                            fax=legacy_user.fax,
                            start_access=legacy_user.start_access,
                            end_access=legacy_user.end_access,
                            roles=new_role,
                            company=new_company,
                        )
                
                role_info = f" with role '{new_role.title}'" if new_role else " without role"
                company_info = f" and company '{new_company.name}'" if new_company else " and no company"
                self.stdout.write(
                    self.style.SUCCESS(f'Migrated: {legacy_user.username}{role_info}{company_info}')
                )
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating {legacy_user.username}: {str(e)}')
                )
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total users in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped (already exists): {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))