from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import IpcUser as LegacyIpcUser
from accounts.models import User as NewUser
from contracts.models.models import Contract, ContractBorder
from contracts.models.SharhKhadamats import ShrhLayer
from initialborders.models.models import InitialBorder


class Command(BaseCommand):
    help = 'Migrate user permissions from rprjgharar to new permission system'

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
        
        # Get all legacy users with their prjgharar relationships
        legacy_users = LegacyIpcUser.objects.using('legacy').prefetch_related('rprjgharar').all()
        total_users = legacy_users.count()
        
        self.stdout.write(f'Found {total_users} users in legacy database')
        
        migrated_users = 0
        skipped_users = 0
        error_count = 0
        
        total_initialborder_perms = 0
        total_contract_perms = 0
        total_contractborder_perms = 0
        total_sharhlayer_perms = 0
        
        for legacy_user in legacy_users:
            try:
                # Find corresponding new user
                new_user = NewUser.objects.filter(username=legacy_user.username).first()
                
                if not new_user:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: User {legacy_user.username} not found in new database')
                    )
                    skipped_users += 1
                    continue
                
                # Get all prjgharar relationships
                prjgharars = legacy_user.rprjgharar.all()
                
                if not prjgharars.exists():
                    self.stdout.write(
                        self.style.WARNING(f'User {legacy_user.username} has no prjgharar relationships')
                    )
                    skipped_users += 1
                    continue
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nProcessing user: {legacy_user.username} with {prjgharars.count()} prjgharar relationships'
                    )
                )
                
                # Collect all unique objects to grant access
                initialborders_to_grant = set()
                contracts_to_grant = set()
                contractborders_to_grant = set()
                sharhlayers_to_grant = set()
                
                for prjgharar in prjgharars:
                    # Get Project (Tarh)
                    if prjgharar.project and prjgharar.project.rtarh:
                        legacy_tarh = prjgharar.project.rtarh
                        legacy_tarh_title = legacy_tarh.titletarh
                        legacy_tarh_dtyp_code = legacy_tarh.dtarh.codetarh if legacy_tarh.dtarh else None
                        
                        # Find InitialBorder
                        if legacy_tarh_dtyp_code:
                            initial_border = InitialBorder.objects.filter(
                                title=legacy_tarh_title,
                                dtyp__code=legacy_tarh_dtyp_code
                            ).first()
                        else:
                            initial_border = InitialBorder.objects.filter(
                                title=legacy_tarh_title
                            ).first()
                        
                        if initial_border:
                            initialborders_to_grant.add(initial_border)
                    
                    # Get Contract (Gharardad)
                    if prjgharar.gharardad:
                        contract = Contract.objects.filter(oldid=prjgharar.gharardad.pk).first()
                        if contract:
                            contracts_to_grant.add(contract)
                    
                    # Get ContractBorder (Project)
                    if prjgharar.project and prjgharar.gharardad:
                        contractborder = ContractBorder.objects.filter(
                            oldid=prjgharar.project.pk,
                            contract__oldid=prjgharar.gharardad.pk
                        ).first()
                        if contractborder:
                            contractborders_to_grant.add(contractborder)
                    
                    # Get all ShrhLayers for this prjgharar
                    shrhlayers = ShrhLayer.objects.filter(oldid=prjgharar.pk)
                    for shrhlayer in shrhlayers:
                        sharhlayers_to_grant.add(shrhlayer)
                
                # Grant permissions in bulk
                if not dry_run:
                    with transaction.atomic():
                        # Grant InitialBorder access
                        if initialborders_to_grant:
                            granted = new_user.grant_bulk_initialborder_access(list(initialborders_to_grant))
                            total_initialborder_perms += granted
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  Granted {granted} InitialBorder permissions'
                                )
                            )
                        
                        # Grant Contract access
                        if contracts_to_grant:
                            granted = new_user.grant_bulk_contract_access(list(contracts_to_grant))
                            total_contract_perms += granted
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  Granted {granted} Contract permissions'
                                )
                            )
                        
                        # Grant ContractBorder access
                        if contractborders_to_grant:
                            granted = new_user.grant_bulk_contractborder_access(list(contractborders_to_grant))
                            total_contractborder_perms += granted
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  Granted {granted} ContractBorder permissions'
                                )
                            )
                        
                        # Grant ShrhLayer access
                        if sharhlayers_to_grant:
                            granted = new_user.grant_bulk_sharhlayer_access(list(sharhlayers_to_grant))
                            total_sharhlayer_perms += granted
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  Granted {granted} ShrhLayer permissions'
                                )
                            )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  DRY RUN: Would grant access to:\n'
                            f'    - {len(initialborders_to_grant)} InitialBorders\n'
                            f'    - {len(contracts_to_grant)} Contracts\n'
                            f'    - {len(contractborders_to_grant)} ContractBorders\n'
                            f'    - {len(sharhlayers_to_grant)} ShrhLayers'
                        )
                    )
                
                migrated_users += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating permissions for user {legacy_user.username}: {str(e)}')
                )
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total users in legacy DB: {total_users}')
        self.stdout.write(self.style.SUCCESS(f'Users migrated: {migrated_users}'))
        self.stdout.write(self.style.WARNING(f'Users skipped: {skipped_users}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        self.stdout.write('\nPermissions granted:')
        self.stdout.write(self.style.SUCCESS(f'  - InitialBorder: {total_initialborder_perms}'))
        self.stdout.write(self.style.SUCCESS(f'  - Contract: {total_contract_perms}'))
        self.stdout.write(self.style.SUCCESS(f'  - ContractBorder: {total_contractborder_perms}'))
        self.stdout.write(self.style.SUCCESS(f'  - ShrhLayer: {total_sharhlayer_perms}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))