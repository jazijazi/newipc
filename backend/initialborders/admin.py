from django.contrib import admin
from leaflet.admin import LeafletGeoAdmin

from initialborders.models.models import (
    InitialBorder,
    InitialBorderDomin,
    #Attachment
    InitialBorderAttachment,
    InitialBorderAttachmentDomain,
    #Metadata
    InitialBorderMetadataPahneh,
    InitialBorderMetadataDarkhastekteshaf,
    InitialBorderMetadataParvaneekteshaf,
    InitialBorderMetadataGovahikashf,
    InitialBorderMetadataParvanebahrebardai,
    InitialBorderMetadataPotansielyabi,
)

admin.site.site_header = 'مدیریت سامانه'
admin.site.index_title = 'صفحه مدیریت'

class InitialBorderAdmin(LeafletGeoAdmin):
    search_fields = ['title', 'dtyp__title']
    list_filter = ['dtyp']
    list_display = ['id','title','dtyp','parentid']

class InitialBorderDominModalAdmin(admin.ModelAdmin):
    list_display = ['id','title','code']

class InitialBorderAttachmentModalAdmin(admin.ModelAdmin):
    pass

class InitialBorderAttachmentDomainModalAdmin(admin.ModelAdmin):
    list_display = ['id','code' , 'name' , 'category' , 'dinitialborder']


admin.site.register(InitialBorder , InitialBorderAdmin)
admin.site.register(InitialBorderDomin , InitialBorderDominModalAdmin)
#Attachment
admin.site.register(InitialBorderAttachment , InitialBorderAttachmentModalAdmin)
admin.site.register(InitialBorderAttachmentDomain , InitialBorderAttachmentDomainModalAdmin)
#Metadata
admin.site.register(InitialBorderMetadataPahneh)
admin.site.register(InitialBorderMetadataDarkhastekteshaf)
admin.site.register(InitialBorderMetadataParvaneekteshaf)
admin.site.register(InitialBorderMetadataGovahikashf)
admin.site.register(InitialBorderMetadataParvanebahrebardai)
admin.site.register(InitialBorderMetadataPotansielyabi)
