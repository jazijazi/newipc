from django.urls import path, include

from initialborders.views.initialborders import (
    InitialBorderListViews,
    InitialBorderDetailViews,
    #contracts
    InitialBorderContractsApiView,
    #domin
    InitialBorderDominListView,
    #metadata
    InitialBorderMetadatDetailsView,
    #attahcment
    InitialBorderAttachmentListView,
    InitialBorderAttachmentDetailView,
    #attachment domain
    InitialBorderAttachmentDomainListApiView,
    InitialBorderAttachmentDomainDetailsApiView,
)


urlpatterns = [
    path('' , InitialBorderListViews.as_view() , name="initialborder-list"), 
    path('<int:pk>/' , InitialBorderDetailViews.as_view() , name="initialborder-detail"),
    path('domins/' , InitialBorderDominListView.as_view() , name="initialborderdomins-list"),
    path('metadata/<int:initialborderpk>/' , InitialBorderMetadatDetailsView.as_view() , name="initialborder-metadata-detail"),
    path('<int:initialborderpk>/attachments/' , InitialBorderAttachmentListView.as_view() , name="initialborder-atach-list"),
    path('attachment/<int:attachmentpk>/' , InitialBorderAttachmentDetailView.as_view() , name="initialborder-atach-detail"),
    path('attachdomains/' , InitialBorderAttachmentDomainListApiView.as_view() , name="initialborder-atach-domain-list"),
    path('attachdomains/<int:attachdomainpk>/' , InitialBorderAttachmentDomainDetailsApiView.as_view() , name="initialborder-atach-domain-detail"),
    path('<int:initialborderpk>/contracts/' , InitialBorderContractsApiView.as_view() , name="initialborder-all-contracts"),

]
