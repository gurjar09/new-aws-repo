from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect
from .urls import *
from .models import *
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
import qrcode
from django.core.files.base import ContentFile
from io import BytesIO
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum,Max
import random
import requests

# 2Factor configuration
TWO_FACTOR_API_KEY = '4ae01fe2-1cb9-11ef-8b60-0200cd936042'

def send_otp_via_sms(mobile_number, otp):
    url = f'https://2factor.in/API/V1/{TWO_FACTOR_API_KEY}/SMS/{mobile_number}/{otp}'
    response = requests.get(url)
    return response.status_code == 200

def generate_otp():
    return str(random.randint(1000, 9999))

def index(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        mobile_number = request.POST.get('mobile_number')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        refer_code = username

        if not username:
            messages.error(request, 'Username must be set')
            return render(request, 'index.html')

        if password1 != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'index.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username is already taken')
            return render(request, 'index.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email is already taken')
            return render(request, 'index.html')
        

        user = User.objects.create_user(username=username, email=email, password=password1)
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        vendor = Vendor.objects.create(user=user, mobile_number=mobile_number, refer_code=refer_code)

        otp = generate_otp()
        user_otp, created = UserOTP.objects.get_or_create(user=user)
        user_otp.otp_secret = otp
        user_otp.save()

        if send_otp_via_sms(mobile_number, otp):
            messages.success(request, 'Registration successful! An OTP has been sent to your mobile number. Please verify it.')
            request.session['username'] = username  
            return redirect(verify_otp)
        else:
            messages.error(request, 'Failed to send OTP. Please try again.')
            user.delete()
            return render(request, 'index.html')

    return render(request, 'index.html')

def verify_otp(request):
    if request.method == 'POST':
        otp = request.POST.get('otp')
        username = request.session.get('username')
        if not username:
            messages.error(request, 'Session expired. Please register again.')
            return redirect(index)

        try:
            user = User.objects.get(username=username)
            user_otp = UserOTP.objects.get(user=user)
        except (User.DoesNotExist, UserOTP.DoesNotExist):
            messages.error(request, 'OTP validation failed. Please request a new OTP.')
            return redirect(index)

        if user_otp.otp_secret == otp:
            messages.success(request, 'OTP verified successfully.')
            return redirect(VendorLogin)  # Replace with your secure area view
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            return render(request, 'verify_otp.html')

    return render(request, 'verify_otp.html')


def resend_otp(request):
    username = request.session.get('username')
    if not username:
        messages.error(request, 'Session expired. Please register again.')
        return redirect(index)

    try:
        user = User.objects.get(username=username)
        vendor = Vendor.objects.get(user=user)
        user_otp, created = UserOTP.objects.get_or_create(user=user)
    except (User.DoesNotExist, Vendor.DoesNotExist, UserOTP.DoesNotExist):
        messages.error(request, 'Unable to resend OTP. Please register again.')
        return redirect(index)

    otp = generate_otp()
    user_otp.otp_secret = otp
    user_otp.save()

    if send_otp_via_sms(vendor.mobile_number, otp):
        messages.success(request, 'A new OTP has been sent to your mobile number.')
    else:
        messages.error(request, 'Failed to send OTP. Please try again.')

    return redirect(verify_otp)

@login_required
def VendorDashboard(request):
    if request.user.is_authenticated:
        try:
            vendor = Vendor.objects.get(user=request.user)
            referral_link = request.build_absolute_uri('/candidateform/?ref={}'.format(vendor.refer_code))
            candidates = Candidate.objects.filter(refer_code=vendor.refer_code)
            num_candidates = candidates.count()
            total_commission = candidates.aggregate(total_commission=Sum('commission'))['total_commission']

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(referral_link)
            qr.make(fit=True)

            img = qr.make_image(fill='black', back_color='white')
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_code_file = ContentFile(buffer.getvalue(), name=f'{vendor.user.username}_qr.png')

            # Save QR code to vendor
            vendor.qr_code.save(qr_code_file.name, qr_code_file)
            vendor.save()

            if request.method == 'POST' and request.FILES.get('profile_picture'):
                profile_picture = request.FILES['profile_picture']
                vendor.profile_image = profile_picture
                vendor.save()

            context = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'shop_name': vendor.shop_name,
                'candidates': candidates,
                'num_candidates': num_candidates,
                'total_commission': total_commission,
                'referral_link': referral_link,
                'qr_code_url': vendor.qr_code.url if vendor.qr_code else None,
            }

            return render(request, 'VendorDashboard.html', context)

        except Vendor.DoesNotExist:
            return render(request, 'usernotfound.html', {'error': 'Vendor details not found'})
    else:
        return render(request, 'usernotfound.html', {'error': 'User not authenticated'})

def candidateform(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        qualification = request.POST.get('qualification')
        mobile_number = request.POST.get('mobile_number')
        email = request.POST.get('email')
        resume = request.FILES.get('resume')
        sector = request.POST.get('sector')
        location = request.POST.get('location')
        refer_code = request.POST.get('refer_code', '')
        Job_Type = request.POST.get('Job_Type')
        submission_time = str(timezone.now())
        

        candidate = Candidate.objects.create(
            first_name=first_name,
            last_name=last_name,
            qualification=qualification,
            mobile_number=mobile_number,
            email=email,
            resume=resume,
            sector=sector,
            location=location,
            refer_code=refer_code,
            Job_Type=Job_Type,
            submission_time=submission_time,
        )

        return redirect(CandidateSuccess, candidate_id=candidate.id)

    else:
        refer_code = request.GET.get('ref', '')
        initial_data = {'refer_code': refer_code}
        return render(request, 'candidateform.html', {'initial_data': initial_data})


def CandidateDetails(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    initial_data = {
        'commission': candidate.commission,
        'totalCommission': candidate.totalCommission,
        'Contact': candidate.Contact,
        'status': candidate.status,
        'Contact_by': candidate.Contact_by,
        'Remark' : candidate.Remark,
        'Payment_Status' : candidate.Payment_Status,
        'Payment_Status' : candidate.Payment_Status,
        'resume': candidate.resume.url if candidate.resume else None
    }
    if request.method == 'POST':
        candidate.commission = request.POST.get('commission')
        candidate.totalCommission = request.POST.get('totalCommission')
        candidate.Contact = request.POST.get('Contact')
        candidate.status = request.POST.get('status')
        candidate.Contact_by = request.POST.get('Contact_by')
        candidate.Remark = request.POST.get('Remark')
        candidate.Payment_Status = request.POST.get('Payment_Status')
        candidate.Payment_complete_date = request.POST.get('Payment_complete_date')
        candidate.save()
        return render(request, 'CandidateDetails.html', {'candidate': candidate, 'initial_data': initial_data})
    return render(request, 'CandidateDetails.html', {'candidate': candidate, 'initial_data': initial_data})

def VendorLogin(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        remember_me = request.POST.get('remember_me')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if remember_me:
                request.session.set_expiry(settings.REMEMBER_ME_EXPIRY)
                request.session['remember_me'] = True
            else:
                request.session.pop('remember_me', None)
            return redirect('VendorDashboard')
        else:
            error_message = "Invalid username or password. Please try again."
            return render(request, 'VendorLogin.html', {'error_message': error_message})
    else:
        return render(request, 'VendorLogin.html')

def VendorLogout(request):
    logout(request)
    return redirect(VendorLogin)

def CandidateSuccess(request, candidate_id):
    return render(request, 'CandidateSuccess.html')


@login_required
def Profile(request):
    if request.user.is_authenticated:
        try:
            vendor = Vendor.objects.get(user=request.user)
            profile_document, created = ProfileDocument.objects.get_or_create(vendor=vendor)

            if request.method == 'POST':
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                shop_name = request.POST.get('shop_name')
                mobile_number = request.POST.get('mobile_number')
                address = request.POST.get('address')
                date_of_birth = request.POST.get('date_of_birth')

                user = request.user
                user.first_name = first_name
                user.last_name = last_name
                user.save()

                vendor.shop_name = shop_name
                vendor.mobile_number = mobile_number
                vendor.address = address
                vendor.date_of_birth = date_of_birth

                vendor.save()

                adhar_card = request.POST.get('adhar_card')
                pan_card = request.POST.get('pan_card')
                adhar_image = request.FILES.get('adhar_image')
                pan_image = request.FILES.get('pan_image')

                profile_document.adhar_card = adhar_card
                profile_document.pan_card = pan_card
                if adhar_image:
                    profile_document.adhar_image = adhar_image
                if pan_image:
                    profile_document.pan_image = pan_image
                profile_document.save()

                return redirect(Profile)

            profileVerification = vendor.profileVerification

            adhar_image_url = profile_document.adhar_image.url if profile_document.adhar_image else None
            pan_image_url = profile_document.pan_image.url if profile_document.pan_image else None

            context = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'shop_name': vendor.shop_name,
                'mobile_number': vendor.mobile_number,
                'address': vendor.address,
                'date_of_birth': vendor.date_of_birth,
                'adhar_card': profile_document.adhar_card,
                'pan_card': profile_document.pan_card,
                'adhar_image_url': adhar_image_url,
                'pan_image_url': pan_image_url,
                'verification_status': profileVerification,
            }
            return render(request, 'Profile.html', context)

        except Vendor.DoesNotExist:
            return render(request, 'usernotfound.html', {'error': 'Vendor details not found'})
        except ProfileDocument.DoesNotExist:
            return render(request, 'Profile.html', {'error': 'Profile document not found'})

    else:
        return render(request, 'usernotfound.html', {'error': 'User not authenticated'})


@login_required
def EstablishmentDetails(request):
    if request.user.is_authenticated:
        try:
            vendor = Vendor.objects.get(user=request.user)
            bussiness_profile, _ = BussinessDetails.objects.get_or_create(vendor=vendor)

            context = {
                'first_name': request.user.first_name.capitalize(),
                'last_name': request.user.last_name.capitalize(),
                'shop_name': vendor.shop_name.capitalize(),
                'mobile_number': vendor.mobile_number,
                'address': vendor.address,
                'date_of_birth': vendor.date_of_birth,
                'gst_number': bussiness_profile.gst_number,
                'Bpan_number': bussiness_profile.Bpan_number,
                'MSME_number': bussiness_profile.MSME_number,
                'Contact_number': bussiness_profile.Contact_number,
                'Gumasta_number': bussiness_profile.Gumasta_number,
                'Busness_email': bussiness_profile.Busness_email,
                'VCname': bussiness_profile.VCname,
                'VCmobile': bussiness_profile.VCmobile,
                'VCaddress': bussiness_profile.VCaddress,
            }
            if request.method == 'POST':
                gst_number = request.POST.get('gst_number')
                Bpan_number = request.POST.get('Bpan_number')
                MSME_number = request.POST.get('MSME_number')
                Contact_number = request.POST.get('Contact_number')
                Gumasta_number = request.POST.get('Gumasta_number')
                Bpan_image = request.FILES.get('Bpan_image')
                gst_image = request.FILES.get('gst_image')
                Gumasta = request.FILES.get('Gumasta')
                MSME_image = request.FILES.get('MSME_image')
                Bphoto_outer = request.FILES.get('Bphoto_outer')
                Bphoto_inside = request.FILES.get('Bphoto_inside')
                Busness_email = request.POST.get('Busness_email')
                VCname = request.POST.get('VCname')
                VCmobile = request.POST.get('VCmobile')
                VCaddress = request.POST.get('VCaddress')

                bussiness_profile.gst_number = gst_number
                bussiness_profile.Bpan_number = Bpan_number
                bussiness_profile.MSME_number = MSME_number
                bussiness_profile.Contact_number = Contact_number
                bussiness_profile.Gumasta_number = Gumasta_number
                bussiness_profile.Busness_email = Busness_email
                bussiness_profile.VCname = VCname
                bussiness_profile.VCmobile = VCmobile
                bussiness_profile.VCaddress = VCaddress

                if Bpan_image:
                    bussiness_profile.Bpan_image = Bpan_image
                if gst_image:
                    bussiness_profile.gst_image = gst_image
                if Gumasta:
                    bussiness_profile.Gumasta = Gumasta
                if MSME_image:
                    bussiness_profile.MSME_image = MSME_image
                if Bphoto_outer:
                    bussiness_profile.Bphoto_outer = Bphoto_outer
                if Bphoto_inside:
                    bussiness_profile.Bphoto_inside = Bphoto_inside

                bussiness_profile.save()

                return redirect(EstablishmentDetails)

            return render(request, 'EstablishmentDetails.html', context)
        except Vendor.DoesNotExist:
            return render(request, 'usernotfound.html', {'error': 'Vendor details not found'})
        except BussinessDetails.DoesNotExist:
            return render(request, 'EstablishmentDetails.html', {'error': 'Business details not found'})
    else:
        return render(request, 'usernotfound.html', {'error': 'User not authenticated'})


@login_required
def Bank_Details(request):
    if request.user.is_authenticated:
        try:
            vendor = Vendor.objects.get(user=request.user)
            bank_details, created = Bank.objects.get_or_create(vendor=vendor)

            preffered_payout_date = [
                ('05', '05'),
                ('15', '15'),
                ('25', '25'),
            ]

            if request.method == 'POST':
                bank_document = request.FILES.get('bank_document')
                account_type = request.POST.get('account_type')
                account_holder_name = request.POST.get('account_holder_name')
                account_number1 = request.POST.get('account_number1')
                account_number2 = request.POST.get('account_number2')
                ifs_code = request.POST.get('ifs_code')
                micr_code = request.POST.get('micr_code')
                bank_name = request.POST.get('bank_name')

                preffered_payout_date = request.POST.getlist('preffered_payout_date')

                if account_number1 != account_number2:
                    return render(request, 'password.html', {'error': 'Account numbers do not match'})

                bank_details.bank_document = bank_document
                bank_details.account_type = account_type
                bank_details.account_holder_name = account_holder_name.capitalize()
                bank_details.account_number1 = account_number1 if account_number1 else None
                bank_details.ifs_code = ifs_code
                bank_details.micr_code = micr_code
                bank_details.bank_name = bank_name
                bank_details.preffered_payout_date = ','.join(preffered_payout_date)
                bank_details.save()

                return redirect(Bank_Details)

            context = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'account_holder_name': bank_details.account_holder_name,
                'account_number1': bank_details.account_number1,
                'ifs_code': bank_details.ifs_code,
                'micr_code': bank_details.micr_code,
                'bank_name': bank_details.bank_name,
                'account_type': bank_details.account_type if bank_details.account_type else '',
                'preffered_payout_date': bank_details.preffered_payout_date.split(',') if bank_details.preffered_payout_date else [],
                'available_payout_dates': preffered_payout_date,
            }
            return render(request, 'VendorBankDetails.html', context)
        
        except Vendor.DoesNotExist:
            return render(request, 'usernotfound.html', {'error': 'Vendor details not found'})
        except Bank.DoesNotExist:
            return render(request, 'VendorBankDetails.html', {'error': 'Bank details not found'})
    else:
        return render(request, 'usernotfound.html', {'error': 'User not authenticated'})


def forgot_password(request):
    if request.method == 'POST':
        mobile_number = request.POST.get('mobile_number')
        user = User.objects.filter(vendor__mobile_number=mobile_number).first()
        if user:
            otp = generate_otp()
            request.session['reset_mobile_number'] = mobile_number
            request.session['reset_otp'] = otp
            if send_otp_via_sms(mobile_number, otp):
                return redirect(verify_otp_for_password_reset)
            else:
                messages.error(request, 'Failed to send OTP. Please try again.')
                return redirect(forgot_password)
        else:
            messages.error(request, 'User with this mobile number does not exist')
            return redirect(forgot_password)
    else:
        return render(request, 'forgot_password.html')

def verify_otp_for_password_reset(request):
    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        if otp_entered == request.session.get('reset_otp'):
            return redirect(reset_password)
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            return render(request, 'otp_for_forgot_password.html')
    return render(request, 'otp_for_forgot_password.html')

def reset_password(request):
    if request.method == 'POST':
        mobile_number = request.session.get('reset_mobile_number')
        user = User.objects.filter(vendor__mobile_number=mobile_number).first()
        if user:
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            if password1 == password2:
                user.set_password(password1)
                user.save()
                messages.success(request, 'Password reset successfully.')
                return redirect(VendorLogin)
            else:
                messages.error(request, 'Passwords do not match.')
        else:
            messages.error(request, 'User with this mobile number does not exist')
    return render(request, 'reset_password.html')
def adminDashBoard(request):
    if request.user.is_authenticated and request.user.is_superuser:
        if request.method == 'POST':
            vendor_id = request.POST.get('vendor_id')
            if vendor_id:
                try:
                    vendor = Vendor.objects.get(pk=vendor_id)
                    vendor.delete()
                    messages.success(request, 'Vendor deleted successfully.')
                    return redirect('admin_dashboard')
                except Vendor.DoesNotExist:
                    messages.error(request, 'Vendor does not exist.')

        try:
            superuser_name = request.user.username.capitalize()
            username_query = request.GET.get('username', '')
            vendors = Vendor.objects.filter(user__username__icontains=username_query)
            total_candidate_commission = Candidate.objects.aggregate(total_commission=Sum('commission'))['total_commission']
            total_vendor_commission = Vendor.objects.aggregate(total_commission_received=Sum('total_commission_received'))['total_commission_received']

            user_data = []
            for vendor in vendors:
                candidates = Candidate.objects.filter(refer_code=vendor.refer_code)
                total_commission = candidates.aggregate(total_commission=Sum('commission'))['total_commission'] or 0
                user_data.append({
                    'user': vendor.user,
                    'shop_name': vendor.shop_name.capitalize(),
                    'mobile_number': vendor.mobile_number,
                    'total_commission': total_commission,  # Ensure this field is used
                    'CommissionReceived': vendor.CommissionReceived,
                    'document_id': getattr(vendor, 'profiledocument', None) and vendor.profiledocument.id,
                    'bussiness_id': getattr(vendor, 'bussinessdetails', None) and vendor.bussinessdetails.id,
                    'bank_id': getattr(vendor, 'bank', None) and vendor.bank.id,
                    'vendor_id': vendor.id,
                })

            vendor_count = Vendor.objects.count()
            total_candidates_all = Candidate.objects.all().count()
            current_month = timezone.now().month
            current_year = timezone.now().year
            vendors_this_month = Vendor.objects.filter(user__date_joined__year=current_year, user__date_joined__month=current_month).count()
            if not user_data:
                no_vendors_message = 'No vendors found.'
                return render(request, 'AdminDashBoard.html', {'no_vendors_message': no_vendors_message, 'superuser_name': superuser_name})

            return render(request, 'AdminDashBoard.html', {
                'user_data': user_data,
                'vendor_count': vendor_count,
                'vendors_this_month': vendors_this_month,
                'total_vendor_commission': total_vendor_commission,
                'total_candidate_commission': total_candidate_commission,
                'superuser_name': superuser_name,
            })
        except User.DoesNotExist:
            return render(request, '404.html', {'error': 'User details not found'})
    else:
        return render(request, '404.html', {'error': 'User not authenticated or not a superuser'})




def vendor_candidates(request, vendor_code):
    try:
        vendor = Vendor.objects.get(refer_code=vendor_code)
        candidates = Candidate.objects.filter(refer_code=vendor_code)
        total_candidates = candidates.count()
        superuser_name = request.user.username.capitalize()

        vendor_name = vendor.user.first_name.capitalize()
        vendor_last_name = vendor.user.last_name.capitalize()

        return render(request, 'VendorsCandidate.html', { 'vendor': vendor, 'candidates': candidates, 'vendor_name': vendor_name, 'vendor_last_name': vendor_last_name, 'total_candidates': total_candidates, 'superuser_name': superuser_name})
    except Vendor.DoesNotExist:
        return render(request, '404.html', {'error': 'Vendor not found'})


def candidateDashboard(request):
    candidates = Candidate.objects.all()
    total_candidates_all = candidates.count()
    superuser_name = request.user.username.capitalize()
    employee_id = None

    if request.user.is_authenticated:
        try:
            employee_id = request.user.employee.employee_id
        except AttributeError:
            pass

    if request.method == 'GET':
        contact_filter = request.GET.get('contact', '')
        contact_by_filter = request.GET.get('contact_by', '')
        refer_code_filter = request.GET.get('refer_code', '')
        name_filter = request.GET.get('name', '')
        mobile_filter = request.GET.get('mobile', '')
        email_filter = request.GET.get('email', '')
        location_filter = request.GET.get('location', '')
        job_preference_filter = request.GET.get('job_preference', '')
        status_filter = request.GET.get('status', '')

        if contact_filter:
            candidates = candidates.filter(Contact__icontains=contact_filter)
        if contact_by_filter:
            candidates = candidates.filter(Contact_by__icontains=contact_by_filter)
        if refer_code_filter:
            candidates = candidates.filter(refer_code__icontains=refer_code_filter)
        if name_filter:
            candidates = candidates.filter(Q(first_name__icontains=name_filter) | Q(last_name__icontains=name_filter))
        if mobile_filter:
            candidates = candidates.filter(mobile_number__icontains=mobile_filter)
        if email_filter:
            candidates = candidates.filter(email__icontains=email_filter)
        if location_filter:
            candidates = candidates.filter(location__icontains=location_filter)
        if job_preference_filter:
            candidates = candidates.filter(sector__icontains=job_preference_filter)
        if status_filter:
            candidates = candidates.filter(status__icontains=status_filter)

    if request.method == 'POST':
        candidate_id = request.POST.get('candidate_id')
        try:
            candidate_to_delete = Candidate.objects.get(pk=candidate_id)
            candidate_to_delete.delete()
            return HttpResponseRedirect(reverse(candidateDashboard))
        except ObjectDoesNotExist:
            pass
        except Exception as e:
            pass

    return render(request, 'candidateDashboard.html', {
        'candidates': candidates,
        'total_candidates_all': total_candidates_all,
        'superuser_name': superuser_name,
        'employee_id': employee_id,
    })

@login_required
def EmployeeDashboard(request):
    try:
        user_name = request.user.username.capitalize()
        username_query = request.GET.get('username', '')
        vendors = Vendor.objects.filter(user__username__icontains=username_query)
        total_candidate_commission = Candidate.objects.aggregate(total_commission=Sum('commission'))['total_commission']
        username = request.user.username
        total_vendor_commission = Vendor.objects.aggregate(total_commission_received=Sum('total_commission_received'))['total_commission_received']
        users = User.objects.filter(is_superuser=False)
        user_data = []
        document_id = None
        bussiness_id = None
        bank_id = None
        for user in users:
            profile = None
            try:
                profile = Vendor.objects.get(user=user)
                document_id = profile.profiledocument.id
                bussiness_id = profile.bussinessdetails.id
                bank_id = profile.bank.id
            except ObjectDoesNotExist:
                pass
            if profile:
                user_data.append({
                    'user': user,
                    'shop_name': profile.shop_name.capitalize(),
                    'mobile_number': profile.mobile_number,
                    'vendor_commission': profile.total_commission_received,
                    'CommissionReceived': profile.CommissionReceived,
                    'document_id': document_id,
                    'bussiness_id': bussiness_id,
                    'bank_id': bank_id,
                })

        vendor_count = Vendor.objects.count()
        total_candidates_all = Candidate.objects.all().count()
        current_month = timezone.now().month
        current_year = timezone.now().year
        vendors_this_month = Vendor.objects.filter(user__date_joined__year=current_year, user__date_joined__month=current_month).count()

        return render(request, 'EmployeeAdminDashboard.html', {'username': username,'user_data': user_data, 'vendor_count': vendor_count, 'vendors_this_month': vendors_this_month, 'total_vendor_commission': total_vendor_commission, 'total_candidate_commission': total_candidate_commission , 'total_candidates_all': total_candidates_all, 'username_query': username_query, 'user_name': user_name})
    except User.DoesNotExist:
        return render(request, '404.html', {'error': 'User details not found'})
    
@login_required
def Employeecandidate(request):
    candidates = Candidate.objects.all()
    total_candidates_all = candidates.count()
    superuser_name = request.user.username

    search_query = request.GET.get('search_query')
    if search_query:
        candidates = candidates.filter(
            Q(first_name__icontains=search_query) | Q(last_name__icontains=search_query) | 
            Q(mobile_number__icontains=search_query) | Q(email__icontains=search_query) | 
            Q(location__icontains=search_query) | Q(sector__icontains=search_query) | 
            Q(status__icontains=search_query)
        )

    return render(request, 'Employeecandidate.html', {'candidates': candidates, 'total_candidates_all': total_candidates_all, 'superuser_name': superuser_name})

@login_required
def Employee_vendorecandidate(request, vendor_code):
    try:
        vendor = Vendor.objects.get(refer_code=vendor_code)
        candidates = Candidate.objects.filter(refer_code=vendor_code)
        total_candidates = candidates.count()
        superuser_name = request.user.username.capitalize()

        vendor_name = vendor.user.first_name.capitalize()
        vendor_last_name = vendor.user.last_name.capitalize()

        return render(request, 'EmployeVendorCandidate.html', { 'vendor': vendor, 'candidates': candidates, 'vendor_name': vendor_name, 'vendor_last_name': vendor_last_name, 'total_candidates': total_candidates, 'superuser_name': superuser_name})
    except Vendor.DoesNotExist:
        return render(request, '404.html', {'error': 'Vendor not found'})
    
def employee_login(request):
    if request.method == 'POST':
        employee_id = request.POST['employee_id']
        password = request.POST['password']
        
        user = authenticate(request, username=employee_id, password=password)
        
        if user is not None:
            login(request, user)
            return redirect(EmployeeDashboard)
        else:
            error_message = "Invalid employee ID or password. Please try again."
            return render(request, 'employee_login.html', {'error_message': error_message})
    else:
        return render(request, 'employee_login.html')

def employee_signup(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        mobile_number = request.POST.get('mobile_number')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        employee_id = request.POST.get('employee_id')

        if not email or not mobile_number or not password1 or not password2 or not employee_id:
            messages.error(request, 'All fields are required')
            return render(request, 'employee_signup.html')

        if password1 != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'employee_signup.html')

        if User.objects.filter(username=employee_id).exists():
            messages.error(request, 'Employee ID is already taken')
            return render(request, 'employee_signup.html')

        user = User.objects.create_user(username=employee_id, email=email, password=password1)
        user.save()

        employee = Employee.objects.create(user=user, mobile_number=mobile_number, employee_id=employee_id)

        login(request, user)

        return redirect(employee_login)
    
    return render(request, 'employee_signup.html')
def employee_logout(request):
    logout(request)
    return redirect(employee_login)
@login_required
def EmployeeDetails(request):
    try:
        employees = Employee.objects.all()
        
        context = {
            'employees': employees,
        }

        return render(request, 'EmployeeDetails.html', context)
    except Employee.DoesNotExist:
        return render(request, '404.html', {'error': 'Employee details not found'})
    


@login_required
def AdminVendorDetails(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    bank_details = Bank.objects.filter(vendor=vendor).first()
    profile_document = ProfileDocument.objects.filter(vendor=vendor).first()
    business_details = BussinessDetails.objects.filter(vendor=vendor).first()
    adhar_image_url = profile_document.adhar_image.url if profile_document and profile_document.adhar_image else None
    pan_image_url = profile_document.pan_image.url if profile_document and profile_document.pan_image else None
    bpan_image_url = business_details.Bpan_image.url if business_details and business_details.Bpan_image else None
    gst_image_url = business_details.gst_image.url if business_details and business_details.gst_image else None
    gumasta_image_url = business_details.Gumasta.url if business_details and business_details.Gumasta else None
    msme_image_url = business_details.MSME_image.url if business_details and business_details.MSME_image else None
    bphoto_outer_image_url = business_details.Bphoto_outer.url if business_details and business_details.Bphoto_outer else None
    bphoto_inside_image_url = business_details.Bphoto_inside.url if business_details and business_details.Bphoto_inside else None
    bank_document_url = bank_details.bank_document.url if bank_details and bank_details.bank_document else None
    
    if request.method == 'POST':
        vendor.user.first_name = request.POST.get('first_name', '')
        vendor.user.last_name = request.POST.get('last_name', '')
        vendor.mobile_number = request.POST.get('mobile_number', '')
        vendor.user.email = request.POST.get('email', '')
        vendor.date_of_birth = request.POST.get('date_of_birth', '')
        vendor.shop_name = request.POST.get('shop_name', '')
        vendor.address = request.POST.get('address', '')
        vendor.profile_verification = request.POST.get('profile_verification', '')
        vendor.save()
        
        if bank_details:
            bank_details.account_holder_name = request.POST.get('account_holder_name', '')
            bank_details.account_number = request.POST.get('account_number', '')
            bank_details.ifs_code = request.POST.get('ifs_code', '')
            bank_details.micr_code = request.POST.get('micr_code', '')
            bank_details.bank_name = request.POST.get('bank_name', '')
            bank_details.save()
        
        if profile_document:
            profile_document.adhar_card = request.POST.get('adhar_card', '')
            profile_document.pan_card = request.POST.get('pan_card', '')
            profile_document.save()
        
        if business_details:
            business_details.gst_number = request.POST.get('gst_number', '')
            business_details.msme_number = request.POST.get('msme_number', '')
            business_details.gumasta_number = request.POST.get('gumasta_number', '')
            business_details.save()
        
        return redirect('AdminVendorDetails', vendor_id=vendor_id)
    
    return render(request, 'AdminVendorDetails.html', {
        'vendor': vendor,
        'bank_details': bank_details,
        'profile_document': profile_document,
        'business_details': business_details,
        'adhar_image_url': adhar_image_url,
        'pan_image_url': pan_image_url,
        'bpan_image_url': bpan_image_url,
        'gst_image_url': gst_image_url,
        'gumasta_image_url': gumasta_image_url,
        'msme_image_url': msme_image_url,
        'bphoto_outer_image_url': bphoto_outer_image_url,
        'bphoto_inside_image_url': bphoto_inside_image_url,
        'bank_document_url' : bank_document_url
    })

@login_required
def EmployeeCandidateDetails(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    initial_data = {
        'commission': candidate.commission,
        'totalCommission': candidate.totalCommission,
        'Contact': candidate.Contact,
        'status': candidate.status,
        'Contact_by' : candidate.Contact_by,
        'commission_Generate_date' : candidate.commission_Generate_date,
        'Remark' : candidate.Remark,
        'resume': candidate.resume.url if candidate.resume else None
    }
    if request.method == 'POST':
        candidate.commission = request.POST.get('commission')
        candidate.totalCommission = request.POST.get('totalCommission')
        candidate.Contact = request.POST.get('Contact')
        candidate.status = request.POST.get('status')
        candidate.Contact_by = request.POST.get('Contact_by')
        candidate.commission_Generate_date = request.POST.get('commission_Generate_date')
        candidate.Remark = request.POST.get('Remark')
        candidate.save()
        return render(request, 'EmployeeCandidateDetails.html', {'candidate': candidate, 'initial_data': initial_data})
    return render(request, 'EmployeeCandidateDetails.html', {'candidate': candidate, 'initial_data': initial_data})

def sitemap(request) :
    return render(request,'sitemap.xml')

def robots(request) :
    return render(request,'robots.txt')




@login_required
def Transections(request):
    try:
        vendor = Vendor.objects.get(user=request.user)
    except Vendor.DoesNotExist:
        return render(request, 'VendorLogin.html', {'error': 'Vendor details not found'})

    
    candidates = Candidate.objects.filter(refer_code=vendor.refer_code,commission__gt=0)
    num_candidates = candidates.count()
    total_commission = candidates.aggregate(total_commission=Sum('commission'))['total_commission']

    context = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'shop_name': vendor.shop_name,
        'candidates': candidates,
        'num_candidates': num_candidates,
        'total_commission': total_commission,
              
    }
    return render(request, 'transactionHistory.html', context)


@login_required
def VendorTransaction(request):
    if not request.user.is_superuser:
        return render(request, 'NotAuthorized.html')

    # Retrieve all vendors and their total commissions
    vendors = Vendor.objects.all()
    vendor_data = []
    total_commission_sum = 0
    
    for index, vendor in enumerate(vendors, start=1):
        total_commission = Candidate.objects.filter(refer_code=vendor.refer_code).aggregate(total_commission=Sum('commission'))['total_commission'] or 0
        total_commission_sum += total_commission
        
        # Check if Bank details exist for the vendor
        try:
            bank_details = Bank.objects.get(vendor=vendor)
            account_number = bank_details.account_number1
            ifsc = bank_details.ifs_code
        except Bank.DoesNotExist:
            account_number = "N/A"
            ifsc = "N/A"
        
        # Get the latest commission_Generate_date and Payment_complete_date for the vendor's candidates
        latest_commission_date = Candidate.objects.filter(refer_code=vendor.refer_code).aggregate(latest_commission_date=Max('commission_Generate_date'))['latest_commission_date'] or "N/A"
        latest_payment_date = Candidate.objects.filter(refer_code=vendor.refer_code).aggregate(latest_payment_date=Max('Payment_complete_date'))['latest_payment_date'] or "N/A"

        vendor_data.append({
            'serial_no': index,
            'vendor_name': vendor.user.get_full_name(),
            'shop_name': vendor.shop_name,
            'account_number': account_number,
            'ifsc': ifsc,
            'total_commission': total_commission,
            'date_of_commission_generation': latest_commission_date,
            'send_commission_date': latest_payment_date,
        })

    context = {
        'vendor_data': vendor_data,
        'total_commission_sum': total_commission_sum,
    }
    
    return render(request, 'VendorTransaction.html', context)