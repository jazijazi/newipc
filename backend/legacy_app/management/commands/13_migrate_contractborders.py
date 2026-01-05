import traceback
from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import (
    Project as LegacyProject,
    ProjectGharar as LegacyProjectGharar,
)
from contracts.models.models import (
    ContractBorder as NewContractBorder,
    Contract as NewContract,
)
from initialborders.models.models import (
    InitialBorder as NewInitialBorder,
    InitialBorderDomin as NewInitialBorderDomin
)


class Command(BaseCommand):
    help = 'Migrate Project to ContractBorder with proper relationships'

    # Map old scale format to new scale integer values
    SCALE_MAPPING = {
        '1:250000': 250000,
        '1:100000': 100000,
        '1:50000': 50000,
        '1:25000': 25000,
        '1:10000': 10000,
        '1:5000': 5000,
        '1:2000': 2000,
        '1:1000': 1000,
        '1:500': 500,
        '1:<500': 499,
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
        
        legacy_projects = LegacyProject.objects.using('legacy').all()
        total_count = legacy_projects.count()
        
        self.stdout.write(f'Found {total_count} projects in legacy database')
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for legacy_project in legacy_projects:
            try:
                # Check if already migrated by oldid
                existing = NewContractBorder.objects.filter(oldid=legacy_project.pk).exists()
                if existing:
                    self.stdout.write(self.style.WARNING(f'Skipping: {legacy_project.titleprj} - already migrated'))
                    skipped_count += 1
                    continue
                
                # Find matching InitialBorder using rtarh
                new_initborder = None
                if legacy_project.rtarh:
                    # Match by title and dtyp.title
                    legacy_tarh_title = legacy_project.rtarh.titletarh
                    legacy_tarh_dtyp_title = legacy_project.rtarh.dtarh.tarhtype if legacy_project.rtarh.dtarh else None
                    
                    if legacy_tarh_dtyp_title:
                        new_initborder = NewInitialBorder.objects.filter(
                            title=legacy_tarh_title,
                            dtyp__title=legacy_tarh_dtyp_title
                        ).first()
                    else:
                        new_initborder = NewInitialBorder.objects.filter(
                            title=legacy_tarh_title
                        ).first()
                    
                    if not new_initborder:
                        self.stdout.write(
                            self.style.ERROR(f'Skipping: InitialBorder not found for {legacy_project.titleprj} (tarh: {legacy_tarh_title})')
                        )
                        skipped_count += 1
                        continue
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Create Default INITIALBORDER FOR: {legacy_project.titleprj}')
                    )
                    # skipped_count += 1
                    if not dry_run:
                        try:
                            default_new_intialborder_domin = NewInitialBorderDomin.objects.filter(code=33).first()
                            new_initborder = NewInitialBorder.objects.create(
                                title = f"{legacy_project.titleprj} (پیشفرض ) ",
                                dtyp = default_new_intialborder_domin,
                                border = legacy_project.border 
                            )
                        except Exception as e:
                            traceback.print_exc()
                            self.stdout.write(
                                self.style.WARNING(f'ERROR Create Default INITIALBORDER FOR: {legacy_project.titleprj} {str(e)}')
                            )
                            continue
                    else:    
                        continue
                
                # Get all contracts (gharardads) related to this project through ProjectGharar
                legacy_project_gharars = LegacyProjectGharar.objects.using('legacy').filter(
                    project=legacy_project
                )
                
                if not legacy_project_gharars.exists():
                    self.stdout.write(
                        self.style.ERROR(f'Skipping: {legacy_project.titleprj} has no related contracts')
                    )
                    skipped_count += 1
                    continue
                
                # Map scale
                new_scale = None
                if legacy_project.scale:
                    new_scale = self.SCALE_MAPPING.get(legacy_project.scale)
                    if not new_scale:
                        self.stdout.write(
                            self.style.WARNING(f'Scale "{legacy_project.scale}" not found in mapping for {legacy_project.titleprj}')
                        )
                
                # Create ContractBorder for each contract relationship
                for project_gharar in legacy_project_gharars:
                    if not project_gharar.gharardad:
                        self.stdout.write(
                            self.style.WARNING(f'ProjectGharar has no gharardad for {legacy_project.titleprj}')
                        )
                        continue
                    
                    # Find the corresponding new Contract by oldid
                    new_contract = NewContract.objects.filter(oldid=project_gharar.gharardad.pk).first()
                    
                    if not new_contract:
                        self.stdout.write(
                            self.style.WARNING(f'Contract not found for {legacy_project.titleprj} (gharardad pk: {project_gharar.gharardad.pk})')
                        )
                        continue
                    
                    if not dry_run:
                        with transaction.atomic():
                            NewContractBorder.objects.create(
                                oldid=legacy_project.pk,
                                title=legacy_project.titleprj,
                                scale=new_scale,
                                border=legacy_project.border,
                                contract=new_contract,
                                initborder=new_initborder
                            )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Migrated: {legacy_project.titleprj} -> Contract: {new_contract.title}')
                    )
                    migrated_count += 1
                
            except Exception as e:
                
                self.stdout.write(
                    self.style.ERROR(f'Error migrating {legacy_project.titleprj}: {str(e)}')
                )
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total projects in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated: {migrated_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))