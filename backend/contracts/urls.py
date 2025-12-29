from django.urls import path, include

from contracts.views.contractviews import (
    ContractListApiViews,
    ContractDetailsApiViews,
    ContractDomainsListApiView,

    ContractBorderListApiView,
    ContractBorderDetailsApiView,
)
from contracts.views.sharhkhadamatviews import (
    SharhkhadamatListApiView,
    SharhkhadamatDetailApiView,

    SharhKhadamatLayerListApiView,
    SharhKhadamatLayerDetailApiView,
)
from contracts.views.commnentsview import(
    CommentListApiView,
    CommentDetailsApiView,
)
from contracts.views.attachmentviews import(
    ContractBorderAttachmentDomainListApiView,
    ContractBorderAttachmentDomainDetailsApiView,

    ContractBorderAttachmentListApiView,
    ContractBorderAttachmentDetailsApiView,
)

urlpatterns = [
    path('' , ContractListApiViews.as_view() , name="contract-list"),
    path('<uuid:contractid>/' , ContractDetailsApiViews.as_view() , name="contract-details"),
    path('domains/' , ContractDomainsListApiView.as_view() , name='contractdomains-list'),

    path('contractborder/' , ContractBorderListApiView.as_view() , name='contractborders-list'),
    path('contractborder/<uuid:pk>/' , ContractBorderDetailsApiView.as_view() , name='contractborders-detail'),

    #Attachment
    path('contractborderattachmentdomain/' , ContractBorderAttachmentDomainListApiView.as_view() , name='contractborderattachmentdomain-list'),
    path('contractborderattachmentdomain/<int:pk>/' , ContractBorderAttachmentDomainDetailsApiView.as_view() , name='contractborderattachmentdomain-details'),

    path('contractborderattachment/<uuid:contractborderid>/' , ContractBorderAttachmentListApiView.as_view() , name='contractborderattachment-list'),
    path('contractborderattachment/<int:contractborderattachmentid>/' , ContractBorderAttachmentDetailsApiView.as_view() , name='contractborderattachment-details'),

    #Sharhkhadamat
    path('sharhkhadamat/<uuid:contractid>/' , SharhkhadamatListApiView.as_view() , name='contract-shrbase-list'),
    path('sharhkhadamat/<uuid:contractid>/<int:shrhbaseid>/' , SharhkhadamatDetailApiView.as_view() , name='contract-shrbase-detail'),

    #Shrhkhadamat Layer
    path('sharhkhadamatlayer/<uuid:contractid>/' , SharhKhadamatLayerListApiView.as_view() , name='contract-shrlyr-list'),
    path('sharhkhadamatlayer/<uuid:contractid>/<int:shrhid>/' , SharhKhadamatLayerDetailApiView.as_view() , name='contract-shrlyr-detail'),

    path('comments/<int:shrhlayerid>/' , CommentListApiView.as_view() , name='comments-list'),
    path('comments/<int:shrhlayerid>/<int:commentid>/' , CommentDetailsApiView.as_view() , name='comments-details'),
]
