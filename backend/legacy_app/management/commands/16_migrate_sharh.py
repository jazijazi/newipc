from django.core.management.base import BaseCommand
from django.db import transaction
from legacy_app.models import (
    Sharhkadamat as LegacySharhkadamat,
)
from accounts.models import User as NewUser
from contracts.models.SharhKhadamats import (
    ShrhBase as NewShrhBase,
    ShrhLayer as NewShrhLayer,
)
from contracts.models.models import (
    ContractBorder as NewContractBorder,
)
from layers.models.models import (
    LayersNames as NewLayersNames,
)

class Command(BaseCommand):
    help = 'Migrate Sharhkadamat to ShrhBase and ShrhLayer'

    # Map old unit names to new UNIT_CHOICES
    UNIT_MAPPING = {
        "تعداد": "تعداد",
        "هکتار": "هکتار",
        "نفرماه": "نفرماه",
        "متراژ": "متراژ",
        "کیلومترمربع": "کیلومترمربع",
    }

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
        
        legacy_sharhkadamats = LegacySharhkadamat.objects.using('legacy').select_related(
            'layer', 'prjgharar', 'prjgharar__project', 'prjgharar__gharardad', 'taeidnahaei_user'
        ).all()
        total_count = legacy_sharhkadamats.count()
        
        self.stdout.write(f'Found {total_count} Sharhkadamat records in legacy database')
        
        migrated_base_count = 0
        migrated_layer_count = 0
        skipped_count = 0
        error_count = 0
        
        # Track created ShrhBase instances to avoid duplicates
        # Key: (contract_id, title, unit, weight, total_volume, unit_price)
        created_shrh_bases = {}
        
        for legacy_shrh in legacy_sharhkadamats:
            try:
                # Validate required relationships
                if not legacy_shrh.prjgharar or not legacy_shrh.prjgharar.gharardad:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: Sharhkadamat {legacy_shrh.id} has no prjgharar or gharardad')
                    )
                    skipped_count += 1
                    continue
                
                if not legacy_shrh.prjgharar.project:
                    self.stdout.write(
                        self.style.WARNING(f'Skipping: Sharhkadamat {legacy_shrh.id} has no project')
                    )
                    skipped_count += 1
                    continue
                
                # Find corresponding ContractBorder
                legacy_project = legacy_shrh.prjgharar.project
                legacy_gharardad = legacy_shrh.prjgharar.gharardad
                
                new_contract_border = NewContractBorder.objects.filter(
                    oldid=legacy_project.pk,
                    contract__oldid=legacy_gharardad.pk
                ).first()
                
                if not new_contract_border:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping: ContractBorder not found for project {legacy_project.pk} '
                            f'and gharardad {legacy_gharardad.pk}'
                        )
                    )
                    skipped_count += 1
                    continue
                
                # Find corresponding LayersNames
                new_layer_name = NewLayersNames.objects.filter(
                    layername_en=legacy_shrh.layer.layername_en,
                    dtyp__code = legacy_shrh.layer.dtyp_id.codetype,
                    lyrgroup_en = legacy_shrh.layer.lyrgroup_en,
                    lyrgroup_fa = legacy_shrh.layer.lyrgroup_fa,
                    layername_fa = legacy_shrh.layer.layername_fa,
                    geometrytype = legacy_shrh.layer.geometrytype,
                ).first()
                
                if not new_layer_name:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Skipping: LayersNames not found for {legacy_shrh.layer.layername_en}'
                        )
                    )
                    skipped_count += 1
                    continue
                
                # Map unit
                new_unit = self.UNIT_MAPPING.get(legacy_shrh.vahed, "تعداد")
                
                # Map scale from project
                new_scale = None
                if legacy_project.scale:
                    new_scale = self.SCALE_MAPPING.get(legacy_project.scale)
                
                # Find or create ShrhBase
                # Create unique key for this ShrhBase
                shrh_base_key = (
                    new_contract_border.contract.id,
                    legacy_shrh.title,
                    new_unit,
                    legacy_shrh.vazn,
                    int(legacy_shrh.hajm),
                    int(legacy_shrh.gheymat)
                )
                
                shrh_base = created_shrh_bases.get(shrh_base_key)
                
                if not shrh_base and not dry_run:
                    # Check if it already exists in database
                    shrh_base = NewShrhBase.objects.filter(
                        contract=new_contract_border.contract,
                        title=legacy_shrh.title,
                        unit=new_unit,
                        weight=legacy_shrh.vazn,
                        total_volume=int(legacy_shrh.hajm),
                        unit_price=int(legacy_shrh.gheymat)
                    ).first()
                    
                    if not shrh_base:
                        # Create new ShrhBase
                        with transaction.atomic():
                            shrh_base = NewShrhBase.objects.create(
                                title=legacy_shrh.title,
                                unit=new_unit,
                                weight=legacy_shrh.vazn,
                                total_volume=int(legacy_shrh.hajm),
                                worked_volume=int(legacy_shrh.hajmkarshde),
                                unit_price=int(legacy_shrh.gheymat),
                                contract=new_contract_border.contract
                            )
                        
                        created_shrh_bases[shrh_base_key] = shrh_base
                        migrated_base_count += 1
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'Created ShrhBase: {shrh_base.title} for contract {new_contract_border.contract.title}')
                        )
                    else:
                        created_shrh_bases[shrh_base_key] = shrh_base
                        self.stdout.write(
                            self.style.WARNING(f'ShrhBase already exists: {shrh_base.title}')
                        )
                
                # Find verified user
                verified_user = None
                if legacy_shrh.taeidnahaei_user:
                    verified_user = NewUser.objects.filter(
                        username=legacy_shrh.taeidnahaei_user.username
                    ).first()
                
                # Check if ShrhLayer already exists
                if shrh_base:
                    existing_layer = NewShrhLayer.objects.filter(
                        oldid=legacy_shrh.pk
                    ).exists()
                    
                    if existing_layer:
                        self.stdout.write(
                            self.style.WARNING(f'Skipping ShrhLayer: already migrated (oldid (prjgharar): {legacy_shrh.prjgharar})')
                        )
                        skipped_count += 1
                        continue
                
                # Create ShrhLayer
                if not dry_run and shrh_base:
                    with transaction.atomic():
                        new_shrh_layer = NewShrhLayer.objects.create(
                            oldid=legacy_shrh.prjgharar.id,
                            shrh_base=shrh_base,
                            layer_name=new_layer_name,
                            scale=new_scale,
                            layer_weight=0,
                            layer_volume=0,
                            is_uploaded=legacy_shrh.layer_bargozary,
                            last_uploaded_date=legacy_shrh.tarikh_bargozary if legacy_shrh.layer_bargozary else None,
                            is_verified=legacy_shrh.taeidnahaei,
                            verified_by=verified_user if legacy_shrh.taeidnahaei else None,
                            verified_at=legacy_shrh.taeidnahaei_tarikh if legacy_shrh.taeidnahaei else None,
                            contractborder=new_contract_border
                        )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Migrated ShrhLayer: {legacy_shrh.title} - {new_layer_name.layername_en} '
                            f'(oldid (prjgharar): {legacy_shrh.prjgharar.id})'
                        )
                    )
                    migrated_layer_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating Sharhkadamat {legacy_shrh.id}: {str(e)}')
                )
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                error_count += 1
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Total Sharhkadamat in legacy DB: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'ShrhBase created: {migrated_base_count}'))
        self.stdout.write(self.style.SUCCESS(f'ShrhLayer migrated: {migrated_layer_count}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count}'))
        self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were saved'))