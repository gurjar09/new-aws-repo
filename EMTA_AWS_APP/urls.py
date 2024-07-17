from .views import *
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    
    path('', index, name='index'),  
    path('VendorSignup/', index, name='index'),
    path('VendorDashboard/', VendorDashboard, name='VendorDashboard'),
    path('VendorLogin/', VendorLogin, name='VendorLogin'),
    path('candidateform/', candidateform, name='candidateform'),
    path('candidate/details/<int:candidate_id>/', CandidateDetails, name='candidate_details'),
    path('VendorLogout/', VendorLogout, name='VendorLogout'),
    path('candidate_success/<int:candidate_id>/', CandidateSuccess, name='candidate_success'),
    path('Profile/', Profile, name='profile_details'),
    path('EstablishmentDetails/', EstablishmentDetails, name='establishment_details'),
    path('Bank_Details/', Bank_Details, name='bank_details'),
    path('forgot_password/', forgot_password, name='forgot_password'),
    path('verify_otp_for_password_reset/', verify_otp_for_password_reset, name='verify_otp_for_password_reset'),
    path('reset_password/', reset_password, name='reset_password'),
    path('adminDashboard/', adminDashBoard, name='admin_dashboard'), 
    path('vendor/<str:vendor_code>/candidates/', vendor_candidates, name='vendor_candidates'),
    path('candidateDashboard/', candidateDashboard, name='candidate_dashboard'),
    path('EmployeeDashboard/', EmployeeDashboard, name='EmployeeDashboard'),
    path('Employeecandidate/', Employeecandidate, name='Employeecandidate'),
    path('EmployeeVendorCandidate/<str:vendor_code>/', Employee_vendorecandidate, name='Employee_vendorecandidate'),
    path('EmployeeSignup/', employee_signup, name='EmployeeSignup'),
    path('EmployeeLogin/', employee_login, name='EmployeeLogin'),
    path('employee_logout/', employee_logout, name='employee_logout'),
    path('EmployeeDetails/', EmployeeDetails, name='employee_details'),
    path('AdminVendorDetails',AdminVendorDetails , name= 'Admin_Vendor_details'),
    path('vendor/<int:vendor_id>/details/', AdminVendorDetails, name='admin_vendor_details'),
    path('admin/vendor/<int:vendor_id>/details/', AdminVendorDetails, name='admin_vendor_details'),
    path('EmployeeCandidateDetails/<int:candidate_id>/', EmployeeCandidateDetails, name='EmployeeCandidateDetails'),
    path('sitemap',sitemap),
    path('robots',robots),
    path('verify-otp/',verify_otp, name='verify_otp'),
    path('resend-otp/', resend_otp, name='resend_otp'),
    path('Transections/', Transections, name='Transections'),
    path('Payment_Transfer/',VendorTransaction, name='Payment_Transfer'),
    
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
