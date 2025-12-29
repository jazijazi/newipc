from django.contrib import admin
from leaflet.admin import LeafletGeoAdmin

from contracts.models.models import (
    ContractDomin,
    Contract,
    ContractBorder,
)
from contracts.models.SharhKhadamats import (
    ShrhBase,
    ShrhLayer,
)
from contracts.models.comments import (
    Comment,
)
from contracts.models.attachment import (
    ContractBorderAttachment,
    ContractBorderAttachmentDomain,
)
class ContractDominAdmin(admin.ModelAdmin):
    list_display = ['title' , 'code']
class ContractAdmin(admin.ModelAdmin):
    list_display = ['title','dtyp','number','start_date','end_date','progress','is_completed',]
    search_fields = ['title' , 'number']
class ContractBorderAdmin(LeafletGeoAdmin):
    list_display = ['title' , 'contract', 'initborder' ,'scale']
    search_fields = ['title']
class ShrhBaseAdmin(admin.ModelAdmin):
    list_display = ['contract' , 'title','unit','weight','total_volume','worked_volume','unit_price' ]
    search_fields = ['title']
class ShrhLayerAdmin(admin.ModelAdmin):
    list_display = ['shrh_base' , 'is_uploaded', 'last_uploaded_date', 'upload_count', 'is_verified', 'verified_by', 'verified_at']
    search_fields = ['shrh_base__title','layer_name__layername_en','layer_name__layername_fa']
    autocomplete_fields = ['shrh_base','layer_name','contractborder']
class CommentAdmin(admin.ModelAdmin):
    list_display = ['sharhlayer' , 'writer' , 'created_at']
    search_fields = []

class ContractBorderAttachmentAdmin(admin.ModelAdmin):
    pass

class ContractBorderAttachmentDomainAdmin(admin.ModelAdmin):
    list_display = ['code' , 'name_en' , 'name_fa']
    search_fields = ['code' , 'name_en' , 'name_fa']


admin.site.register(ContractDomin,ContractDominAdmin)
admin.site.register(Contract,ContractAdmin)
admin.site.register(ContractBorder,ContractBorderAdmin)

admin.site.register(ShrhBase , ShrhBaseAdmin)
admin.site.register(ShrhLayer , ShrhLayerAdmin)

admin.site.register(Comment , CommentAdmin)

admin.site.register(ContractBorderAttachment , ContractBorderAttachmentAdmin)
admin.site.register(ContractBorderAttachmentDomain , ContractBorderAttachmentDomainAdmin)