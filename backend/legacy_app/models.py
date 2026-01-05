from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.gis.db import models as gis_models
from datetime import date
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

class Ostans(models.Model):
    name_fa = models.CharField(verbose_name="نام استان" , max_length=100 , unique=True , null=True , blank=True)
    name_en = models.CharField(verbose_name="نام استان به لاتین" , max_length=100 , unique=True , null=True , blank=True)
    border = gis_models.MultiPolygonField(srid=4326, blank=False, null=False)

    class Meta:
        managed = False
        db_table = 'prjapi_ostans'

class SherkatEjraei(models.Model):
    name        = models.CharField(verbose_name="نام شرکت" , max_length=100, blank=False, null=False, unique=False)
    code        = models.CharField(verbose_name="کد شناسایی شرکت" , max_length=100 , blank=True, null=True, unique=False)
    typ         = models.CharField(verbose_name="نوع شرکت",max_length=100, blank=True, null=True, unique=False)
    service_typ = models.CharField(verbose_name="نوع خدمات",max_length=100, blank=True, null=True, unique=False)
    callnumber  = models.CharField(verbose_name="شماره تماس",max_length=100, blank=True, null=True, unique=False)
    address     = models.CharField(verbose_name="آدرس",max_length=255, blank=True, null=True, unique=False)
    comment     = models.CharField(verbose_name="توضیحات",max_length=255, blank=True, null=True, unique=False)

    class Meta:
        managed = False
        db_table = 'prjapi_sherkatejraei'

class IpcAPI(models.Model):
    apiurl = models.CharField(max_length=100, blank=True, null=True)
    apiname = models.CharField(max_length=100, blank=True, null=True)
    apidesc = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'permitapi_ipcapi'

class IpcTools(models.Model):
    toolname = models.CharField(unique=True, max_length=100, blank=False, null=False)
    tooldesc = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'permitapi_ipctools'

class IpcRole(models.Model):
    apis = models.ManyToManyField(IpcAPI, blank=False, related_name='roles', related_query_name='role')
    tools = models.ManyToManyField(IpcTools, blank=True, related_name='tools', related_query_name='tools')
    rolename = models.CharField(unique=True, max_length=100, blank=False, null=False)
    roledesc = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'permitapi_ipcrole'

class IpcUser(AbstractUser):
    username_validator = RegexValidator(r'^[0-9a-zA-Z]*$', 'فقط حروف و اعداد استفاده کنید')
    phone_validator = RegexValidator(regex=r'^989\d{9}$',message="شماره تماس باید با 989 شروع شود و دقیقاً 12 رقم باشد.")
    username = models.CharField(
      _("username"),
      max_length=150,
      unique=True,
      help_text=_(
          "اجباری.کمتر از 150 کاراکتر. فقط حروف و اعداد استفاده کنید"
      ),
      validators=[username_validator],
      error_messages={
          "unique": _("کاربر با این نام کاربری موجود است"),
      },
    )
    user_try_login_limit = models.PositiveIntegerField(default=0,null=False,blank=False) #check with setting.USER_TRY_LOGIN_LIMITAION
    first_name = models.CharField(verbose_name="نام لاتین" , max_length=255)
    last_name = models.CharField(verbose_name="نام خانوادگی لاتین" , max_length=255)
    email = models.CharField(verbose_name="ایمیل" , max_length=255, unique=True)
    password = models.CharField(verbose_name="رمز عبور" , max_length=255)
    roles = models.ForeignKey(IpcRole, on_delete=models.SET_NULL, related_name="rrole", blank=True, null=True)
    rprjgharar = models.ManyToManyField('ProjectGharar', related_name='ruserprjgharar', related_query_name='quserprjgharar')
    # rfield = models.ManyToManyField(FieldAccess, related_name='ruserfield', related_query_name='rquserfield')
    
    first_name_fa = models.CharField(verbose_name="نام فارسی", max_length=255, blank=True, null=True)
    last_name_fa = models.CharField(verbose_name="نام خانوادگی فارسی", max_length=255, blank=True, null=True)
    address = models.CharField(verbose_name="آدرس", max_length=255, blank=True, null=True)
    phonenumber = models.CharField(
        verbose_name="شماره تماس",
        max_length=255,
        blank=True,
        null=True,
        validators=[phone_validator]
    )
    codemeli = models.CharField(verbose_name="کد ملی", max_length=255, blank=True, null=True)
    fax = models.CharField(verbose_name="فکس", max_length=255, blank=True, null=True)

    start_access = models.DateField(verbose_name="تاریخ شروع دسترسی",auto_now=False,auto_now_add=False,null=True,blank=True)
    end_access = models.DateField(verbose_name="تاریخ پایان دسترسی",auto_now=False,auto_now_add=False,null=True,blank=True)
    sherkat = models.ForeignKey(SherkatEjraei, on_delete=models.SET_NULL, related_name="rusers", blank=True, null=True)


    # Add these lines to fix the clash
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='legacy_user_set',
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='legacy_user_set',
        blank=True,
    )

    class Meta:
        managed = False
        db_table = 'permitapi_ipcuser'

class DTarh(models.Model):
    tarhtype = models.CharField(max_length=100, unique=True)
    codetarh = models.IntegerField(unique=True)

    class Meta:
        managed = False
        db_table = 'prjapi_dtarh'

class Tarh(models.Model):
    titletarh = models.CharField(max_length=200, unique=False, blank=True, null=True)
    border = gis_models.MultiPolygonField(srid=4326, blank=True, null=True)
    dtarh = models.ForeignKey(DTarh, on_delete=models.SET_NULL, related_name="rtarhdtarh", blank=True, null=True)
    parentid = models.ForeignKey('self', on_delete=models.CASCADE, related_name="rparenttarh", blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'prjapi_tarh'


class BaseTarhShenasnameh(models.Model):
    # All tarh shenasnameh inherit from this class
    rtarh = models.OneToOneField('Tarh' , on_delete=models.CASCADE, related_name='%(class)s_rshntarh') #related_name must be unique
    # this fields are common in all shn's
    name        = models.CharField(verbose_name="نام",max_length=100, unique=False, blank=True, null=True)
    masahat     = models.FloatField(verbose_name="مساحت به کیلومترمربع",unique=False, blank=True, null=True)
    malekiyat   = models.CharField(verbose_name="مالکیت",max_length=100, unique=False, blank=True, null=True)
    ostan       = models.CharField(verbose_name="استان",max_length=100, unique=False, blank=True, null=True)
    shahrestan  = models.CharField(verbose_name="شهرستان",max_length=100, unique=False, blank=True, null=True)

    def __str__(self):
        return f"شناسنامه {self.rtarh.titletarh}"

    class Meta:
        abstract = True


class TarhShnPahneh(BaseTarhShenasnameh):
    
    class Meta:
        managed = False
        db_table = 'prjapi_tarhshnpahneh'

class TarhShnDarkhastekteshaf(BaseTarhShenasnameh):
    cadastre      = models.CharField(verbose_name="شماره کاداستر",max_length=100, unique=False, blank=True, null=True)
    noemademadani = models.CharField(verbose_name="نوع ماده معدنی",max_length=100, unique=False, blank=True, null=True)
    organs        = models.CharField(verbose_name="ارگان های استعلام شونده",max_length=250, unique=False, blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'prjapi_tarhshndarkhastekteshaf'

class TarhShnParvaneekteshaf(BaseTarhShenasnameh):
    cadastre        = models.CharField(verbose_name="شماره کاداستر",max_length=100, unique=False, blank=True, null=True)
    noemademadani   = models.CharField(verbose_name="نوع ماده معدنی",max_length=100, unique=False, blank=True, null=True)
    shomareparvaneh = models.CharField(verbose_name="شماره پروانه",max_length=100, unique=False, blank=True, null=True)
    tarikhparvane   = models.DateField(verbose_name="تاریخ پروانه",auto_now=False,auto_now_add=False,null=True,blank=True)
    tarikhetebar    = models.DateField(verbose_name="تاریخ اعتبار",auto_now=False,auto_now_add=False,null=True,blank=True)
    
    class Meta:
        managed = False
        db_table = 'prjapi_tarhshnparvaneekteshaf'

class TarhShnGovahikashf(BaseTarhShenasnameh):
    cadastre           = models.CharField(verbose_name="شماره کاداستر",max_length=100, unique=False, blank=True, null=True)
    noemademadani      = models.CharField(verbose_name="نوع ماده معدنی",max_length=100, unique=False, blank=True, null=True)
    shomareparvaneh    = models.CharField(verbose_name="شماره پروانه",max_length=100, unique=False, blank=True, null=True)
    tarikhparvane      = models.DateField(verbose_name="تاریخ پروانه",auto_now=False,auto_now_add=False,null=True,blank=True)
    tarietebargovahi   = models.DateField(verbose_name="تاریخ اعتبار گواهی",auto_now=False,auto_now_add=False,null=True,blank=True)
    zakhireehtemali    = models.FloatField(verbose_name="ذخیره احتمالی به تن",unique=False, blank=True, null=True)
    zakhireghatei      = models.FloatField(verbose_name="ذخیره قطعی به تن",unique=False, blank=True, null=True)
    ayarehad           = models.FloatField(verbose_name="عیار حد به درصد",unique=False, blank=True, null=True)
    ayaremeyangin      = models.FloatField(verbose_name="عیار میانگین به درصد",unique=False, blank=True, null=True)
    shomaregovahikashf = models.CharField(verbose_name="شماره گواهی کشف",max_length=100, unique=False, blank=True, null=True)
    tarikhsodurgivahikashf = models.DateField(verbose_name="تاریخ صدور گواهی کشف",auto_now=False,auto_now_add=False,null=True,blank=True)
        
    class Meta:
        managed = False
        db_table = 'prjapi_tarhshngovahikashf'

class TarhShnParvanebahrebardai(BaseTarhShenasnameh):
    cadastre          = models.CharField(verbose_name="شماره کاداستر",max_length=100, unique=False, blank=True, null=True)
    noemademadani     = models.CharField(verbose_name="نوع ماده معدنی",max_length=100, unique=False, blank=True, null=True)
    shomareparvaneh   = models.CharField(verbose_name="شماره پروانه",max_length=100, unique=False, blank=True, null=True)
    tarikhparvane     = models.DateField(verbose_name="تاریخ پروانه",auto_now=False,auto_now_add=False,null=True,blank=True)
    tarietebarparvane = models.DateField(verbose_name="تاریخ اعتبار پروانه",auto_now=False,auto_now_add=False,null=True,blank=True)
    zakhireehtemali   = models.FloatField(verbose_name="ذخیره احتمالی به تن",unique=False, blank=True, null=True)
    zakhireghatei     = models.FloatField(verbose_name="ذخیره قطعی به تن",unique=False, blank=True, null=True)
    ayarehad          = models.FloatField(verbose_name="عیار حد به درصد",unique=False, blank=True, null=True)
    ayaremeyangin     = models.FloatField(verbose_name="عیار میانگین به درصد",unique=False, blank=True, null=True)
    estekhrajsaleyane = models.FloatField(verbose_name=" استخراج سالیانه به تن",unique=False, blank=True, null=True)
        
    class Meta:
        managed = False
        db_table = 'prjapi_tarhshnparvanebahrebardai'

class TarhShnPotansielyabi(BaseTarhShenasnameh):
    noemademadani = models.CharField(verbose_name="نوع ماده معدنی",max_length=100, unique=False, blank=True, null=True)
        
    class Meta:
        managed = False
        db_table = 'prjapi_tarhshnpotansielyabi'


class DTarhAttachment(models.Model):
    code = models.IntegerField(verbose_name="کد پیوست" , unique=True , error_messages={'unique': "کد پیوست باید یکتا باشد.",})
    name = models.CharField(verbose_name="عنوان نوع پیوست",max_length=100, unique=False, blank=False, null=False)
    category = models.CharField(verbose_name="دسته بندی",max_length=100, unique=False, blank=False, null=False)
    dtarh = models.ForeignKey(DTarh, on_delete=models.SET_NULL, related_name="rdtarhattachment", blank=True, null=Tarh)

    class Meta:
        managed = False
        db_table = 'prjapi_dtarhattachment'

def dynamic_upload_path_TarhAttachment(instance, filename):
    return f'prjapi/tarhattachments/tarh_{instance.rtarh.id}/{filename}'

class TarhAttachment(models.Model):
    upload_date = models.DateTimeField(verbose_name="تاریخ ساخت پیوست",auto_now_add=True)
    writer = models.ForeignKey(IpcUser, on_delete=models.SET_NULL, related_name="user_tarhattachment", blank=True, null=True) 
    writed_date = models.DateTimeField(verbose_name="تاریخ نوشتن پیوست",auto_now_add=False,blank=True,null=True)
    rtarh = models.ForeignKey(Tarh, on_delete=models.CASCADE, blank=False, null=False, related_name='rtarhattachment')
    dtyp_attach = models.ForeignKey(DTarhAttachment, on_delete=models.SET_NULL, related_name="dtyp_tarhattachment", blank=True, null=True)
    file = models.FileField(
            verbose_name="فایل",
            blank=False,
            upload_to=dynamic_upload_path_TarhAttachment,
        )
    
    class Meta:
        managed = False
        db_table = 'prjapi_tarhattachment'


class DGharar(models.Model):
    gharartype = models.CharField(max_length=100, unique=True)
    codetype = models.IntegerField(unique=True)

    class Meta:
        managed = False
        db_table = 'prjapi_dgharar'

class Layers(models.Model):
    dtyp_id = models.ForeignKey(DGharar, on_delete=models.SET_NULL, related_name="rlyrsdtyp", blank=True, null=True)
    lyrgroup_en = models.CharField(max_length=40, unique=False, blank=True, null=True)
    lyrgroup_fa = models.CharField(max_length=40, unique=False, blank=True, null=True)
    layername_en = models.CharField(max_length=40, unique=False, blank=True, null=True)
    layername_fa = models.CharField(max_length=40, unique=False, blank=True, null=True)
    geometrytype = models.CharField(max_length=20, unique=False, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'prjapi_layers'

class Gharardad(models.Model):
    titlegh = models.CharField(max_length=200, unique=True,error_messages={'unique': "قراردادی با این عنوان هم‌اکنون وجود دارد"})
    dtyp = models.ForeignKey(DGharar, on_delete=models.SET_NULL, related_name="rprjdtyp", blank=True, null=True)
    ghararNo = models.CharField(max_length=100, blank=True, null=True, unique=True,error_messages={'unique': "شماره قرارداد تکراری است"})
    ostan = models.CharField(max_length=50, blank=True, null=True, unique=False)
    startprj = models.DateField(blank=True, null=True)
    endprj = models.DateField(blank=True, null=True)
    pishraft = models.FloatField(default=0)
    khatemeh = models.BooleanField(default=False)
    department = models.CharField(verbose_name="بخش مربوطه",default="-",max_length=100, unique=False, blank=True, null=True)
    sherkatejraei = models.ManyToManyField('SherkatEjraei', related_name="rgharardads", blank=True,)
    #new fields
    mablagh = models.BigIntegerField(verbose_name="مبلغ قرارداد",validators=[
            MinValueValidator(0, message="مبلغ قرارداد نمی‌تواند کمتر از صفر باشد.")
        ],null=True,blank=True)
    elhaghye = models.BooleanField(verbose_name="الحاقیه دارد",default=False,blank=False,null=False)
    mablaghe_elhaghye = models.BigIntegerField(verbose_name="مبلغ الحاقیه",validators=[
            MinValueValidator(0, message="مبلغ الحاقیه نمی‌تواند کمتر از صفر باشد.")
        ],blank=True,null=True)
    tarikh_elhaghye = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'prjapi_gharardad'

class Project(models.Model):
    SCALE_CHOICES = [
        ('1:250000' , '1:250000'), #250K
        ('1:100000' , '1:100000'), #100K 
        ('1:50000' , '1:50000'),  #50K 
        ('1:25000' , '1:25000'),  #25K 
        ('1:10000' , '1:10000'),  #10K 
        ('1:5000' , '1:5000'),   #5K 
        ('1:2000' , '1:2000'),   #2K 
        ('1:1000' , '1:1000'),   #1K 
        ('1:500' , '1:500'),    #0.5K
        ('1:<500' , '1:<500')    #less 0.5k 
    ]
    titleprj = models.CharField(max_length=200, unique=True)
    scale = models.CharField(verbose_name="مقیاس",choices=SCALE_CHOICES,blank=True,null=True)
    rtarh = models.ForeignKey(Tarh , on_delete=models.SET_NULL, related_name="rprjtarh", blank=True, null=True)
    border = gis_models.MultiPolygonField(srid=4326, blank=True, null=True)
    rgharar = models.ManyToManyField(Gharardad, through='ProjectGharar', blank=False, related_name='rgharar', related_query_name='qgharar')
    
    class Meta:
        managed = False
        db_table = 'prjapi_project'

class ProjectGharar(models.Model):
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, blank=True, null=True)
    gharardad = models.ForeignKey(Gharardad, on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'prjapi_projectgharar'

class DPrjAttach(models.Model):
    code = models.IntegerField(verbose_name="کد" , unique=True)
    name_en = models.CharField(verbose_name="نام لاتین",max_length=100, unique=False, blank=False, null=False)
    name_fa = models.CharField(verbose_name="نام فارسی",max_length=100, unique=False, blank=False, null=False)
    typ = models.CharField(verbose_name="نوع",max_length=100, unique=False, blank=False, null=False)
   
    class Meta:
        managed = False
        db_table = 'prjapi_dprjattach'


def dynamic_upload_path_ProjectAttachment(instance, filename):
    return f'prjapi/projectattachments/project_{instance.rprjgharar.project.id}/gharardad_{instance.rprjgharar.gharardad.id}/{filename}'


class ProjectAttachment(models.Model):
    upload_date = models.DateTimeField(verbose_name="تاریخ ساخت",auto_now_add=True)
    writer = models.ForeignKey(IpcUser, on_delete=models.SET_NULL, related_name="user_projectattachment", blank=True, null=True) 
    rprjgharar = models.ForeignKey(ProjectGharar, on_delete=models.CASCADE, blank=False, null=False, related_name='rprjgharar_projectattachment')
    dtyp = models.ForeignKey(DPrjAttach, on_delete=models.SET_NULL, related_name="dtyp_projectattachment", blank=True, null=True)
    
    file = models.FileField(
            verbose_name="فایل",
            blank=False,
            upload_to=dynamic_upload_path_ProjectAttachment,
        )
    
    class Meta:
        managed = False
        db_table = 'prjapi_projectattachment'

class Sharhkadamat(models.Model):
    title = models.CharField(verbose_name="عنوان" , max_length=250, blank=False, null=False, unique=False)
    layer = models.ForeignKey(Layers, verbose_name="لایه",  on_delete=models.CASCADE, related_name="rsharhkadamatlayer", blank=False, null=False)
    prjgharar = models.ForeignKey(ProjectGharar, verbose_name="prjgharar", on_delete=models.CASCADE, related_name='rshrhkhadamatprjgharar' , blank=False, null=False,)
    layer_bargozary = models.BooleanField(verbose_name="بار‌گذاری شده",default=False,blank=False,null=False)
    layer_baresi =  models.BooleanField(verbose_name="بررسی شده",default=False,blank=False,null=False)
    vazn = models.IntegerField(
        verbose_name="وزن این بند از شرح خدمات",
        validators=[
            MinValueValidator(0, message="وزن این بند از شرح خدمات نمیتواند کمتر از صفر باشد"),
            MaxValueValidator(100, message="وزن این بند از شرح خدمات نمیتواند بیشتر از صد باشد")
        ],
        default=0,
        blank=False,
        null=False
    )
    vahed = models.CharField(verbose_name="واحد" ,default="تعداد", max_length=100, blank=False, null=False, unique=False)
    hajm = models.FloatField(verbose_name="حجم" ,default=1, blank=False, null=False, unique=False)
    gheymat = models.BigIntegerField(verbose_name="قیمت" ,default=1, blank=False, null=False, unique=False)
    hajmkarshde = models.FloatField(verbose_name="حجم کار شده" ,default=1, blank=False, null=False, unique=False)
    
    tarikh_bargozary = models.DateField(verbose_name="تاریخ آخرین بارگذاری",default=date(2023,3,21),null=False,blank=False)
    
    taeidnahaei = models.BooleanField(verbose_name="تایید نهایی",default=False,blank=False,null=False)
    taeidnahaei_user = models.ForeignKey(IpcUser,verbose_name="کاربر تاییدنهایی کننده",on_delete=models.SET_NULL,blank=True,null=True)
    taeidnahaei_tarikh = models.DateField(verbose_name="تاریخ تاییدنهایی شده",null=True,blank=True)
   
    class Meta:
        managed = False
        db_table = 'prjapi_sharhkadamat' 

class RasterData(models.Model):
    sharhkadamat = models.ForeignKey(Sharhkadamat,verbose_name="شرح خدمات",on_delete=models.CASCADE,related_name="rraster",blank=False,null=False)
    uuid = models.CharField(verbose_name="uuid" ,max_length=100, blank=False, null=False, unique=False)

    class Meta:
        managed = False
        db_table = 'prjapi_rasterdata'


def FeatureAttachmentdynamic_upload_path(instance, filename):

    return f'prjapi/featureattachment/{instance.content_type.model}/{instance.object_id}/{filename}'


class FeatureAttachment(models.Model):
    upload_date = models.DateTimeField(verbose_name="تاریخ ساخت",auto_now_add=True)
    writer = models.ForeignKey(IpcUser, on_delete=models.SET_NULL, blank=True, null=True) 
    
    content_type = models.ForeignKey(ContentType,related_name='legacy_featureattachment_set', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    linked_to_project = GenericForeignKey('content_type', 'object_id')

    file = models.FileField(
            verbose_name="فایل",
            blank=False,
            upload_to=FeatureAttachmentdynamic_upload_path,
        )
    
    class Meta:
        managed = False
        db_table = 'prjapi_featureattachment'