from django.urls import path, include


from report.views.views import (
    ReportMain,
)
from report.views.layerreport import (
    ReportLayers
)
from report.views.contracts import (
    ReportContracts,
    ReportContractsByCompany,
    ReportContractsBySharh
)




urlpatterns = [
    path('' , ReportMain.as_view() , name="main"),

    # layer report
    path('layers/' , ReportLayers.as_view() , name="layer-report-main"),

    

    # contract report
    path('contracts/' , ReportContracts.as_view() , name="contracts-main"),
    path('contracts/bycompany/' , ReportContractsByCompany.as_view() , name="contracts-bycompany"),
    path('contracts/bysharh/' , ReportContractsBySharh.as_view() , name="contracts-bysharh"),

]
