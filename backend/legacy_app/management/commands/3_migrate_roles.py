from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import IpcRole as LegacyRole
from accounts.models import Roles as NewRole


class Command(BaseCommand):
    help = 'Migrate roles data from legacy database to new database (title and desc only)'

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
        
        # Get all roles from legacy database
        legacy_roles = LegacyRole.objects.using('legacy').all()
        total_count = legacy_roles.count()
        
        self.stdout.write(f'Found {total_count} roles in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for legacy_role in legacy_roles:
            try:
                # Check if role already exists in new database
                exists = NewRole.objects.filter(title=legacy_role.rolename).exists()
                
                if exists:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: {legacy_role.rolename} - already exists')
                    )
                    skipped_count += 1
                    continue
                
                if not dry_run:
                    with transaction.atomic():
                        NewRole.objects.create(
                            pk=legacy_role.pk,
                            title=legacy_role.rolename,
                            desc=legacy_role.roledesc
                            # apis and tools will remain empty
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Migrated: {legacy_role.rolename}')
                )
                migrated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating {legacy_role.rolename}: {str(e)}')
                )
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total roles in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped (already exists): {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        self.stdout.write(self.style.WARNING('\nNote: apis and tools fields were left empty'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))