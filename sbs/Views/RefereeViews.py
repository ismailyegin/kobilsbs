from datetime import date
from io import BytesIO

import reportlab.rl_config
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User, Group
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from reportlab.lib.utils import ImageReader
# pdf
from reportlab.pdfgen import canvas
from zeep import Client

from accounts.models import Forgot
from sbs.Forms.CategoryItemForm import CategoryItemForm
from sbs.Forms.CommunicationForm import CommunicationForm
from sbs.Forms.DisabledCommunicationForm import DisabledCommunicationForm
from sbs.Forms.DisabledPersonForm import DisabledPersonForm
from sbs.Forms.DisabledUserForm import DisabledUserForm
from sbs.Forms.GradeFormReferee import GradeFormReferee
from sbs.Forms.IbanFormJudge import IbanFormJudge
from sbs.Forms.PersonForm import PersonForm
from sbs.Forms.RefereeSearchForm import RefereeSearchForm
from sbs.Forms.ReferenceRefereeForm import RefereeForm
from sbs.Forms.SearchClupForm import SearchClupForm
from sbs.Forms.UserForm import UserForm
from sbs.Forms.VisaForm import VisaForm
from sbs.Forms.VisaSeminarForm import VisaSeminarForm
from sbs.models import Judge, CategoryItem, Communication, Level
from sbs.models.EnumFields import EnumFields
from sbs.models.JudgeApplication import JudgeApplication
from sbs.models.Person import Person
from sbs.models.PreRegistration import PreRegistration
# from sbs.models.ReferenceReferee import ReferenceReferee
from sbs.models.ReferenceCoach import ReferenceCoach
from sbs.models.ReferenceReferee import ReferenceReferee
from sbs.models.VisaSeminar import VisaSeminar
from sbs.services import general_methods

# resim
reportlab.rl_config.warnOnMissingFontGlyphs = 0

from django.conf import settings


@login_required
def return_add_referee(request):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    user_form = UserForm()
    person_form = PersonForm()
    communication_form = CommunicationForm()
    iban_form=IbanFormJudge()

    if request.method == 'POST':

        user_form = UserForm(request.POST)
        person_form = PersonForm(request.POST, request.FILES)
        communication_form = CommunicationForm(request.POST)
        iban_form = IbanFormJudge(request.POST)

        mail = request.POST.get('email')

        if User.objects.filter(email=mail) or ReferenceCoach.objects.exclude(status=ReferenceCoach.DENIED).filter(
                email=mail) or ReferenceReferee.objects.exclude(status=ReferenceReferee.DENIED).filter(
            email=mail) or PreRegistration.objects.exclude(status=PreRegistration.DENIED).filter(
            email=mail):
            messages.warning(request, 'Mail adresi başka bir kullanici tarafından kullanilmaktadir.')
            return render(request, 'hakem/hakem-ekle.html',
                          {'user_form': user_form, 'person_form': person_form,
                           'communication_form': communication_form, 'iban_form': iban_form})

        tc = request.POST.get('tc')
        if Person.objects.filter(tc=tc) or ReferenceCoach.objects.exclude(status=ReferenceCoach.DENIED).filter(
                tc=tc) or ReferenceReferee.objects.exclude(status=ReferenceReferee.DENIED).filter(
            tc=tc) or PreRegistration.objects.exclude(status=PreRegistration.DENIED).filter(tc=tc):
            messages.warning(request, 'Tc kimlik numarasi sisteme kayıtlıdır. ')
            return render(request, 'hakem/hakem-ekle.html',
                          {'user_form': user_form, 'person_form': person_form,
                           'communication_form': communication_form, 'iban_form': iban_form})

        name = request.POST.get('first_name')
        surname = request.POST.get('last_name')
        year = request.POST.get('birthDate')
        year = year.split('/')

        client = Client('https://tckimlik.nvi.gov.tr/Service/KPSPublic.asmx?WSDL')
        if not (client.service.TCKimlikNoDogrula(tc, name, surname, year[2])):
            messages.warning(request, 'Tc kimlik numarasi ile isim  soyisim dogum yılı  bilgileri uyuşmamaktadır. ')
            return render(request, 'hakem/hakem-ekle.html',
                          {'user_form': user_form, 'person_form': person_form,
                           'communication_form': communication_form, 'iban_form': iban_form})












        if user_form.is_valid() and person_form.is_valid() and communication_form.is_valid() and iban_form.is_valid():
            user = User()
            user.username = user_form.cleaned_data['email']
            user.first_name = user_form.cleaned_data['first_name']
            user.last_name = user_form.cleaned_data['last_name']
            user.email = user_form.cleaned_data['email']
            group = Group.objects.get(name='Hakem')
            password = User.objects.make_random_password()
            user.set_password(password)
            user.is_active = True
            user.save()

            log = str(user.get_full_name()) + " Hakemi  ekledi"
            log = general_methods.logwrite(request, request.user, log)


            user.groups.add(group)
            user.save()


            person = person_form.save(commit=False)
            communication = communication_form.save(commit=False)
            person.save()
            communication.save()

            judge = Judge(user=user, person=person, communication=communication)
            judge.iban=iban_form.cleaned_data['iban']
            judge.save()


            # subject, from_email, to = 'Halter - Hakem Bilgi Sistemi Kullanıcı Giriş Bilgileri', 'no-reply@twf.gov.tr:81', user.email
            # text_content = 'Aşağıda ki bilgileri kullanarak sisteme giriş yapabilirsiniz.'
            # html_content = '<p> <strong>Site adresi: </strong> <a href="http://sbs.halter.gov.tr:81/"></a>sbs.halter.gov.tr<</p>'
            # html_content = html_content + '<p><strong>Kullanıcı Adı:  </strong>' + user.username + '</p>'
            # html_content = html_content + '<p><strong>Şifre: </strong>' + password + '</p>'
            # msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
            # msg.attach_alternative(html_content, "text/html")
            # msg.send()

            fdk = Forgot(user=user, status=False)
            fdk.save()

            html_content = ''
            subject, from_email, to = 'Bilgi Sistemi Kullanıcı Bilgileri', 'no-reply@halter.gov.tr', user.email
            html_content = '<h2>TÜRKİYE HALTER FEDERASYONU BİLGİ SİSTEMİ</h2>'
            html_content = html_content + '<p><strong>Kullanıcı Adınız :' + str(fdk.user.username) + '</strong></p>'
            html_content = html_content + '<p> <strong>Site adresi:</strong> <a href="https://sbs.halter.gov.tr:9443/newpassword?query=' + str(
                fdk.uuid) + '">https://sbs.halter.gov.tr:9443/sbs/profil-guncelle/?query=' + str(fdk.uuid) + '</p></a>'
            msg = EmailMultiAlternatives(subject, '', from_email, [to])
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            messages.success(request, 'Hakem Başarıyla Kayıt Edilmiştir.')

            return redirect('sbs:hakemler')

        else:

            for x in user_form.errors.as_data():
                messages.warning(request, user_form.errors[x][0])

    return render(request, 'hakem/hakem-ekle.html',
                  {'user_form': user_form, 'person_form': person_form,
                   'communication_form': communication_form,'iban_form':iban_form})


@login_required
def return_referees(request):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    referees = Judge.objects.none()
    searchClupForm = SearchClupForm()
    user_form = RefereeSearchForm()
    if request.method == 'POST':
        searchClupForm = SearchClupForm(request.POST)
        user_form = RefereeSearchForm(request.POST)
        branch = request.POST.get('branch')
        grade = request.POST.get('definition')
        visa = request.POST.get('visa')
        firstName = request.POST.get('first_name')
        lastName = request.POST.get('last_name')
        email = request.POST.get('email')
        # print(firstName, lastName, email, branch, grade, visa)
        if not (firstName or lastName or email or branch or grade or visa):
            referees = Judge.objects.all()
        else:
            query = Q()
            if lastName:
                query &= Q(user__last_name__icontains=lastName)
            if firstName:
                query &= Q(user__first_name__icontains=firstName)
            if email:
                query &= Q(user__email__icontains=email)
            if branch:
                query &= Q(grades__branch=branch, grades__status='Onaylandı')
            if grade:
                query &= Q(grades__definition__name=grade, grades__status='Onaylandı')
            if visa == 'VISA':
                print('visa ')
                query &= Q(visa__startDate__year=timezone.now().year)
            referees = Judge.objects.filter(query).distinct()
            if visa == 'NONE':
                referees = referees.exclude(visa__startDate__year=timezone.now().year).distinct()

    return render(request, 'hakem/hakemler.html',
                  {'referees': referees, 'user_form': user_form, 'branch': searchClupForm})


@login_required
def return_level(request):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    category_item_form = CategoryItemForm();

    if request.method == 'POST':

        category_item_form = CategoryItemForm(request.POST)

        if category_item_form.is_valid():

            categoryItem = CategoryItem(name=category_item_form.cleaned_data['name'])
            categoryItem.forWhichClazz = "REFEREE_GRADE"
            categoryItem.save()

            return redirect('sbs:seviye')

        else:

            messages.warning(request, 'Alanları Kontrol Ediniz')
    categoryitem = CategoryItem.objects.filter(forWhichClazz="REFEREE_GRADE")
    return render(request, 'hakem/seviye.html',
                  {'category_item_form': category_item_form, 'categoryitem': categoryitem})


@login_required
def categoryItemDelete(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():
        try:
            obj = CategoryItem.objects.get(pk=pk)
            obj.delete()
            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except CategoryItem.DoesNotExist:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})

    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})


@login_required
def categoryItemUpdate(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    categoryItem = CategoryItem.objects.get(id=pk)
    category_item_form = CategoryItemForm(request.POST or None, instance=categoryItem)
    if request.method == 'POST':
        if category_item_form.is_valid():
            category_item_form.save()
            messages.success(request, 'Başarıyla Güncellendi')
            return redirect('sbs:seviye')
        else:
            messages.warning(request, 'Alanları Kontrol Ediniz')

    return render(request, 'hakem/seviyeDuzenle.html',
                  {'category_item_form': category_item_form})


@login_required
def deleteReferee(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():
        try:
            obj = Judge.objects.get(pk=pk)
            log = str(obj.user.get_full_name()) + " Hakemi sildi."
            log = general_methods.logwrite(request, request.user, log)
            obj.delete()
            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except Judge.DoesNotExist:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})

    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})


@login_required
def refencedeleteReferee(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():
        try:
            obj = ReferenceReferee.objects.get(pk=pk)
            obj.status = ReferenceReferee.DENIED
            obj.save()

            log = str(obj.first_name) + " " + str(obj.last_name) + "     Hakem basvurusu reddedildi"
            log = general_methods.logwrite(request, request.user, log)

            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except Judge.DoesNotExist:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})

    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})


@login_required
def refenceapprovalReferee(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    reference = ReferenceReferee.objects.get(pk=pk)
    if request.method == 'POST' and request.is_ajax():
        try:

            if reference.status == ReferenceReferee.WAITED:
                user = User()
                user.username = reference.email
                user.first_name = reference.first_name
                user.last_name = reference.last_name
                user.email = reference.email
                user.is_active = True
                user.save()
                group = Group.objects.get(name='Hakem')
                user.groups.add(group)

                user.save()

                person = Person()
                person.tc = reference.tc
                person.motherName = reference.motherName
                person.fatherName = reference.fatherName
                person.profileImage = reference.profileImage
                person.birthDate = reference.birthDate
                person.bloodType = reference.bloodType
                person.birthplace = reference.birthplace
                if reference.gender == 'Erkek':
                    person.gender = Person.MALE
                else:
                    person.gender = Person.FEMALE
                person.save()
                communication = Communication()
                communication.postalCode = reference.postalCode
                communication.phoneNumber = reference.phoneNumber
                communication.phoneNumber2 = reference.phoneNumber2
                communication.address = reference.address
                communication.city = reference.city
                communication.country = reference.country
                communication.save()

                judge = Judge(user=user, person=person, communication=communication)
                judge.iban = reference.iban
                judge.save()

                grade = Level(definition=reference.kademe_definition,
                              startDate=reference.kademe_startDate,
                              branch=EnumFields.HALTER.value)
                grade.levelType = EnumFields.LEVELTYPE.GRADE
                grade.status = Level.APPROVED
                grade.isActive = True
                grade.save()

                judge.grades.add(grade)
                judge.save()

                reference.status = ReferenceReferee.APPROVED
                reference.save()

                messages.success(request, 'Hakem Başarıyla Eklenmiştir')

                fdk = Forgot(user=user, status=False)
                fdk.save()
                print(fdk)

                html_content = ''
                subject, from_email, to = 'Bilgi Sistemi Kullanıcı Bilgileri', 'no-reply@halter.gov.tr', user.email
                html_content = '<h2>TÜRKİYE HALTER FEDERASYONU BİLGİ SİSTEMİ</h2>'
                html_content = html_content + '<p><strong>Kullanıcı Adınız :' + str(fdk.user.username) + '</strong></p>'
                html_content = html_content + '<p> <strong>Site adresi:</strong> <a href="https://sbs.halter.gov.tr:9443/newpassword?query=' + str(
                    fdk.uuid) + '">https://sbs.halter.gov.tr:9443/sbs/profil-guncelle/?query=' + str(fdk.uuid) + '</p></a>'
                msg = EmailMultiAlternatives(subject, '', from_email, [to])
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                log = str(user.get_full_name()) + " Hakem basvurusu onaylandi"
                log = general_methods.logwrite(request, request.user, log)


            else:
                messages.success(request, 'Hakem daha önce onaylanmıştır.')

            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except Judge.DoesNotExist:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})

    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})






@login_required
def referenceUpdateReferee(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    # judge = Judge.objects.get(pk=pk)
    # user = User.objects.get(pk=judge.user.pk)
    # person = Person.objects.get(pk=judge.person.pk)
    # communication = Communication.objects.get(pk=judge.communication.pk)
    # user_form = UserForm(request.POST or None, instance=user)
    # person_form = PersonForm(request.POST or None, request.FILES or None, instance=person)
    # communication_form = CommunicationForm(request.POST or None, instance=communication)
    # grade_form = judge.grades.all()
    # visa_form = judge.visa.all()
    refere = ReferenceReferee.objects.get(pk=pk)
    refere_form = RefereeForm(request.POST or None, request.FILES or None, instance=refere,initial={'kademe_definition': refere.kademe_definition})
    if request.method == 'POST':

        mail = request.POST.get('email')
        if mail != refere.email:

            if User.objects.filter(email=mail) or ReferenceCoach.objects.exclude(status=ReferenceCoach.DENIED).filter(
                    email=mail) or ReferenceReferee.objects.exclude(status=ReferenceReferee.DENIED).filter(
                email=mail) or PreRegistration.objects.exclude(status=PreRegistration.DENIED).filter(
                email=mail):
                messages.warning(request, 'Mail adresi başka bir kullanici tarafından kullanilmaktadir.')
                return render(request, 'hakem/HakemBasvuruUpdate.html',
                              {'preRegistrationform': refere_form})

        tc = request.POST.get('tc')
        if tc != refere.tc:

            if Person.objects.filter(tc=tc) or ReferenceCoach.objects.exclude(status=ReferenceCoach.DENIED).filter(
                    tc=tc) or ReferenceReferee.objects.exclude(status=ReferenceReferee.DENIED).filter(
                tc=tc) or PreRegistration.objects.exclude(status=PreRegistration.DENIED).filter(tc=tc):
                messages.warning(request, 'Tc kimlik numarasi sisteme kayıtlıdır. ')
                return render(request, 'hakem/HakemBasvuruUpdate.html',
                              {'preRegistrationform': refere_form})

        name = request.POST.get('first_name')
        surname = request.POST.get('last_name')
        year = request.POST.get('birthDate')
        year = year.split('/')

        client = Client('https://tckimlik.nvi.gov.tr/Service/KPSPublic.asmx?WSDL')
        if not (client.service.TCKimlikNoDogrula(tc, name, surname, year[2])):
            messages.warning(request, 'Tc kimlik numarasi ile isim  soyisim dogum yılı  bilgileri uyuşmamaktadır. ')
            return render(request, 'hakem/HakemBasvuruUpdate.html',
                          {'preRegistrationform': refere_form})















        if refere_form.is_valid():
            refere_form.save()
            messages.success(request, 'Hakem Başvurusu Güncellendi')
            # return redirect('sbs:hakemler')
        else:
            messages.warning(request, 'Alanları Kontrol Ediniz')

    return render(request, 'hakem/HakemBasvuruUpdate.html',
                  {'preRegistrationform': refere_form})

@login_required
def updateReferee(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    judge = Judge.objects.get(pk=pk)
    user = User.objects.get(pk=judge.user.pk)
    person = Person.objects.get(pk=judge.person.pk)
    communication = Communication.objects.get(pk=judge.communication.pk)
    user_form = UserForm(request.POST or None, instance=user)
    person_form = PersonForm(request.POST or None, request.FILES or None, instance=person)
    communication_form = CommunicationForm(request.POST or None, instance=communication)
    iban_form=IbanFormJudge(request.POST or None, instance=judge)

    grade_form = judge.grades.all()
    visa_form = judge.visa.all()
    if request.method == 'POST':

        mail = request.POST.get('email')
        if mail != judge.user.email:

            if User.objects.filter(email=mail) or ReferenceCoach.objects.exclude(status=ReferenceCoach.DENIED).filter(
                    email=mail) or ReferenceReferee.objects.exclude(status=ReferenceReferee.DENIED).filter(
                email=mail) or PreRegistration.objects.exclude(status=PreRegistration.DENIED).filter(
                email=mail):
                messages.warning(request, 'Mail adresi başka bir kullanici tarafından kullanilmaktadir.')
                return render(request, 'hakem/hakemDuzenle.html',
                              {'user_form': user_form, 'communication_form': communication_form,
                               'person_form': person_form, 'judge': judge, 'grade_form': grade_form,
                               'visa_form': visa_form, 'iban_form': iban_form, })

        tc = request.POST.get('tc')
        if tc != judge.person.tc:
            if Person.objects.filter(tc=tc) or ReferenceCoach.objects.exclude(status=ReferenceCoach.DENIED).filter(
                    tc=tc) or ReferenceReferee.objects.exclude(status=ReferenceReferee.DENIED).filter(
                tc=tc) or PreRegistration.objects.exclude(status=PreRegistration.DENIED).filter(tc=tc):
                messages.warning(request, 'Tc kimlik numarasi sisteme kayıtlıdır. ')
                return render(request, 'hakem/hakemDuzenle.html',
                              {'user_form': user_form, 'communication_form': communication_form,
                               'person_form': person_form, 'judge': judge, 'grade_form': grade_form,
                               'visa_form': visa_form, 'iban_form': iban_form, })

        name = request.POST.get('first_name')
        surname = request.POST.get('last_name')
        year = request.POST.get('birthDate')
        year = year.split('/')

        client = Client('https://tckimlik.nvi.gov.tr/Service/KPSPublic.asmx?WSDL')
        if not (client.service.TCKimlikNoDogrula(tc, name, surname, year[2])):
            messages.warning(request, 'Tc kimlik numarasi ile isim  soyisim dogum yılı  bilgileri uyuşmamaktadır. ')
            return render(request, 'hakem/hakemDuzenle.html',
                          {'user_form': user_form, 'communication_form': communication_form,
                           'person_form': person_form, 'judge': judge, 'grade_form': grade_form,
                           'visa_form': visa_form, 'iban_form': iban_form, })












        if user_form.is_valid() and person_form.is_valid() and communication_form.is_valid() and iban_form.is_valid():

            user.username = user_form.cleaned_data['email']
            user.first_name = user_form.cleaned_data['first_name']
            user.last_name = user_form.cleaned_data['last_name']
            user.email = user_form.cleaned_data['email']
            user.save()

            log = str(user.get_full_name()) + " Hakemi güncelledi"
            log = general_methods.logwrite(request, request.user, log)






            iban_form.save()

            person_form.save()
            communication_form.save()


            messages.success(request, 'Hakem Başarıyla Güncellendi')
            # return redirect('sbs:hakemler')
        else:
            messages.warning(request, 'Alanları Kontrol Ediniz')

    return render(request, 'hakem/hakemDuzenle.html',
                  {'user_form': user_form, 'communication_form': communication_form,
                   'person_form': person_form, 'judge': judge, 'grade_form': grade_form,
                   'visa_form': visa_form,'iban_form':iban_form,})


@login_required
def updateRefereeProfile(request):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')

    user = request.user
    referee_user = Judge.objects.get(user=user)
    person = Person.objects.get(pk=referee_user.person.pk)
    communication = Communication.objects.get(pk=referee_user.communication.pk)
    user_form = DisabledUserForm(request.POST or None, instance=user)
    person_form = DisabledPersonForm(request.POST or None, request.FILES or None, instance=person)
    communication_form = DisabledCommunicationForm(request.POST or None, instance=communication)
    password_form = SetPasswordForm(request.user, request.POST)

    if request.method == 'POST':
        data = request.POST.copy()
        data['bloodType'] = "AB Rh+"
        data['gender'] = "Erkek"
        person_form = DisabledPersonForm(data)

        if person_form.is_valid() and password_form.is_valid():
            if len(request.FILES)>0:
                person.profileImage = request.FILES['profileImage']
                person.save()
                messages.success(request, 'Profil Fotoğrafı Başarıyla Güncellenmiştir.')

            user.set_password(password_form.cleaned_data['new_password2'])
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Şifre Başarıyla Güncellenmiştir.')
            return redirect('sbs:hakem-profil-guncelle')



        elif person_form.is_valid() and not password_form.is_valid():
            if len(request.FILES)>0:
                person.profileImage = request.FILES['profileImage']
                person.save()
                messages.success(request, 'Profil Fotoğrafı Başarıyla Güncellenmiştir.')
            else:
                messages.warning(request, 'Alanları Kontrol Ediniz')
            return redirect('sbs:hakem-profil-guncelle')


        elif not person_form.is_valid() and password_form.is_valid():
            user.set_password(password_form.cleaned_data['new_password2'])
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Şifre Başarıyla Güncellenmiştir.')
            return redirect('sbs:hakem-profil-guncelle')

        else:
            messages.warning(request, 'Alanları Kontrol Ediniz.')

            return redirect('sbs:hakem-profil-guncelle')

    return render(request, 'hakem/hakem-profil-guncelle.html',
                  {'user_form': user_form, 'communication_form': communication_form,
                   'person_form': person_form, 'password_form': password_form})


@login_required
def hakem_kademe_ekle(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')

    referee = Judge.objects.get(pk=pk)
    grade_form = GradeFormReferee()
    category_item_form = CategoryItemForm()
    if request.method == 'POST':
        grade_form = GradeFormReferee(request.POST, request.FILES)
        category_item_form = CategoryItemForm(request.POST, request.FILES)

        if grade_form.is_valid() and grade_form.cleaned_data['dekont'] is not None and request.POST.get(
                'branch') is not None:
            grade = Level(definition=grade_form.cleaned_data['definition'],
                          startDate=grade_form.cleaned_data['startDate'],
                          dekont=grade_form.cleaned_data['dekont'],
                          branch=grade_form.cleaned_data['branch'])
            grade.levelType = EnumFields.LEVELTYPE.GRADE
            grade.status = Level.WAITED
            grade.isActive = True
            grade.save()
            for item in referee.grades.all():
                if item.branch == grade.branch:
                    item.isActive = False
                    item.save()

            referee.grades.add(grade)
            referee.save()

            log = str(referee.user.get_full_name()) + " Kademe eklendi"
            log = general_methods.logwrite(request, request.user, log)






            messages.success(request, 'Kademe Başarıyla Eklenmiştir.')
            return redirect('sbs:hakem-duzenle', pk=pk)

        else:
            messages.warning(request, 'Alanları Kontrol Ediniz')

    grade_form.fields['definition'].queryset = CategoryItem.objects.filter(forWhichClazz='REFEREE_GRADE')
    return render(request, 'hakem/hakem-kademe-ekle.html',
                  {'grade_form': grade_form})


@login_required
def kademe_onay(request, grade_pk, referee_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    grade = Level.objects.get(pk=grade_pk)
    referee = Judge.objects.get(pk=referee_pk)
    try:
        for item in referee.grades.all():
            if item.branch == grade.branch:
                item.isActive = False
                item.save()
        grade.status = Level.APPROVED
        grade.isActive = True
        grade.save()

        log = str(referee.user.get_full_name()) + " Kademe onaylandi"
        log = general_methods.logwrite(request, request.user, log)

        messages.success(request, 'Kademe   Onaylanmıştır')
    except:
        messages.warning(request, 'Lütfen yeniden deneyiniz.')
    return redirect('sbs:hakem-duzenle', pk=referee_pk)


@login_required
def kademe_reddet(request, grade_pk, referee_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    belt = Level.objects.get(pk=grade_pk)
    belt.status = Level.DENIED
    belt.save()

    referee = Judge.objects.get(pk=referee_pk)
    log = str(referee.user.get_full_name()) + " Kademe reddedildi"
    log = general_methods.logwrite(request, request.user, log)

    messages.success(request, 'Kademe Onaylanmıştır')
    return redirect('sbs:hakem-duzenle', pk=referee_pk)


@login_required
def kademe_update(request, grade_pk, referee_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    grade = Level.objects.get(pk=grade_pk)
    referee = Judge.objects.get(pk=referee_pk)
    categoryItem = Level.objects.get(pk=grade_pk)
    grade_form = GradeFormReferee(request.POST or None, request.FILES or None, instance=grade,
                                  initial={'definition': grade.definition})
    if request.method == 'POST':
        if grade_form.is_valid():
            grade_form.save()
            if grade.status != Level.APPROVED:
                grade.status = Level.WAITED
                grade.save()

                log = str(referee.user.get_full_name()) + " Kademe guncellendi"
                log = general_methods.logwrite(request, request.user, log)
            messages.success(request, 'Kademe Başarılı bir şekilde güncellenmiştir.')
            return redirect('sbs:hakem-duzenle', pk=referee_pk)

        else:

            messages.warning(request, 'Alanları Kontrol Ediniz')

    return render(request, 'hakem/hakem-kademe-güncelle.html',
                  {'grade_form': grade_form})


@login_required
def kademe_delete(request, grade_pk, referee_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():
        try:

            obj = Level.objects.get(pk=grade_pk)
            referee = Judge.objects.get(pk=referee_pk)
            referee.grades.remove(obj)

            log = str(referee.user.get_full_name()) + " Kademe silindi "
            log = general_methods.logwrite(request, request.user, log)
            obj.delete()
            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except Level.DoesNotExist:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})
    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})


@login_required
def vısa_ekle(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')

    referee = Judge.objects.get(pk=pk)
    visa_form = VisaForm()
    category_item_form = CategoryItemForm()

    if request.method == 'POST':
        visa_form = VisaForm(request.POST, request.FILES)
        category_item_form = CategoryItemForm(request.POST, request.FILES)

        try:
            visa = Level(dekont=request.POST.get('dekont'), branch=request.POST.get('branch'))
            visa.startDate = date(int(request.POST.get('startDate')), 1, 1)

            visa.definition = CategoryItem.objects.get(forWhichClazz='VISA_REFEREE')
            visa.levelType = EnumFields.LEVELTYPE.VISA
            visa.status = Level.APPROVED
            for item in referee.visa.all():
                if item.branch == visa.branch:
                    item.isActive = False
                    item.save()
            visa.isActive = True
            visa.save()
            referee.visa.add(visa)
            referee.save()

            log = str(referee.user.get_full_name()) + " hakem  Vize eklendi"
            log = general_methods.logwrite(request, request.user, log)


            messages.success(request, 'Vize Başarıyla Eklenmiştir.')
            return redirect('sbs:hakem-duzenle', pk=pk)
        except:
            messages.warning(request, 'Alanları Kontrol Ediniz')

    return render(request, 'hakem/vize-ekle.html', {'grade_form': visa_form, 'category_item_form': category_item_form})


@login_required
def visa_onay(request, grade_pk, referee_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    visa = Level.objects.get(pk=grade_pk)
    visa.status = Level.APPROVED
    visa.save()
    referee = Judge.objects.get(pk=referee_pk)
    log = str(referee.user.get_full_name()) + " vize onaylandi"
    log = general_methods.logwrite(request, request.user, log)

    messages.success(request, 'Vize onaylanmıştır.')
    return redirect('sbs:hakem-duzenle', pk=referee_pk)


@login_required
def visa_reddet(request, grade_pk, referee_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    visa = Level.objects.get(pk=grade_pk)
    visa.status = Level.DENIED
    visa.save()
    referee = Judge.objects.get(pk=referee_pk)
    log = str(referee.user.get_full_name()) + " vize reddedildi"
    log = general_methods.logwrite(request, request.user, log)

    messages.warning(request, 'Vize Reddedilmiştir.')
    return redirect('sbs:hakem-duzenle', pk=referee_pk)


@login_required
def vize_update(request, grade_pk, referee_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    grade = Level.objects.get(pk=grade_pk)
    referee = Judge.objects.get(pk=referee_pk)
    grade_form = VisaForm(request.POST or None, request.FILES or None, instance=grade)

    if request.method == 'POST':
        if grade_form.is_valid():
            grade.save()
            if grade.status != Level.APPROVED:
                grade.status = Level.WAITED
                grade.save()

                log = str(referee.user.get_full_name()) + " vize guncellendi"
                log = general_methods.logwrite(request, request.user, log)


            messages.success(request, 'Vize Başarılı bir şekilde güncellenmiştir.')
            return redirect('sbs:hakem-duzenle', pk=referee_pk)
        else:
            messages.warning(request, 'Alanları Kontrol Ediniz')
    return render(request, 'hakem/hakem-vize-güncelle.html',
                  {'grade_form': grade_form})


@login_required
def vize_delete(request, grade_pk, referee_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():
        try:

            obj = Level.objects.get(pk=grade_pk)
            referee = Judge.objects.get(pk=referee_pk)
            referee.visa.remove(obj)

            log = str(referee.user.get_full_name()) + " hakem vize silindi"
            log = general_methods.logwrite(request, request.user, log)

            obj.delete()

            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except Level.DoesNotExist:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})
    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})


@login_required
def return_visaSeminar(request):
    perm = general_methods.control_access_judge(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')


    user=request.user

    seminar = VisaSeminar.objects.filter(forWhichClazz='REFEREE')
    print('ben geldim ')
    for item in seminar:
        print(item)


    if request.method == 'POST':
        if user.groups.filter(name='Hakem').exists():
            vizeSeminer = VisaSeminar.objects.get(pk=request.POST.get('pk'))
            judge = Judge.objects.get(user=request.user)
            try:
                if request.FILES['file']:
                    document = request.FILES['file']
                    data = JudgeApplication()
                    data.dekont = document
                    data.judge = judge
                    data.save()
                    vizeSeminer.judgeApplication.add(data)
                    vizeSeminer.save()
                    print('işlem tamam ')

                    messages.success(request, 'Vize Seminerine Başvuru  gerçekleşmiştir.')
                    return redirect('sbs:hakem-visa-seminar-basvuru')
            except:
                messages.warning(request, 'Lütfen yeniden deneyiniz')



    return render(request, 'hakem/Hakem-VizeSeminer.html', {'competitions': seminar})


# visaseminer ekle
@login_required
def visaSeminar_ekle(request):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    visaSeminar = VisaSeminarForm()
    if request.method == 'POST':
        visaSeminar = VisaSeminarForm(request.POST)
        if visaSeminar.is_valid():

            visa = visaSeminar.save()
            visa.forWhichClazz = 'REFEREE'
            visa.save()
            messages.success(request, 'Vize Semineri Başari  Kaydedilmiştir.')

            return redirect('sbs:hakem-visa-seminar')
        else:

            messages.warning(request, 'Alanları Kontrol Ediniz')

    return render(request, 'hakem/hakem-visaSeminerEkle.html',
                  {'competition_form': visaSeminar})


@login_required
def visaSeminar_duzenle(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')

    seminar = VisaSeminar.objects.get(pk=pk)
    referee = seminar.referee.all()
    competition_form = VisaSeminarForm(request.POST or None, instance=seminar)
    if request.method == 'POST':
        if competition_form.is_valid():
            competition_form.save()
            messages.success(request, 'Vize Seminer Başarıyla Güncellenmiştir.')

            return redirect('sbs:hakem-visa-seminar')
        else:

            messages.warning(request, 'Alanları Kontrol Ediniz')

    return render(request, 'hakem/hakem-VizeSeminerGüncelle.html',
                  {'competition_form': competition_form, 'competition': seminar, 'athletes': referee})


@login_required
def visaSeminar_sil(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():
        try:
            obj = VisaSeminar.objects.get(pk=pk)
            obj.delete()
            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except Competition.DoesNotExist:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})

    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})


@login_required
def choose_referee(request, pk):
    perm = general_methods.control_access(request)
    if not perm:
        logout(request)
        return redirect('accounts:login')
    user =request.user
    visa = VisaSeminar.objects.get(pk=pk)
    coa = []
    for item in visa.referee.all():
        coa.append(item.user.pk)
    judge = Judge.objects.exclude(user__id__in=coa)

    if request.method == 'POST':
        athletes1 = request.POST.getlist('selected_options')
        if athletes1:
            for x in athletes1:
                if not visa.referee.filter(user_id__in=x):
                    visa.referee.add(x)
                    visa.save()
        return redirect('sbs:hakem-seminar-duzenle', pk=pk)
    return render(request, 'hakem/hakem-vizeseminerHakemEkle.html', {'athletes': judge})


@login_required
def visaSeminar_Delete_Referee(request, pk, competition):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():
        try:
            visa = VisaSeminar.objects.get(pk=competition)
            visa.referee.remove(Judge.objects.get(pk=pk))
            visa.save()
            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})

    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})


@login_required
def referenceStatus_reddet(request, pk):
    reference = ReferenceReferee.objects.get(pk=pk)
    if reference.status == ReferenceReferee.WAITED:
        reference.status = ReferenceReferee.DENIED
        reference.save()

        html_content = ''
        subject, from_email, to = 'Bilgi Sistemi', 'no-reply@halter.gov.tr', reference.email
        html_content = '<h2>TÜRKİYE HALTER FEDERASYONU BİLGİ SİSTEMİ</h2>'
        html_content = html_content + '<p><strong>Başvurunuz reddedilmiştir.</strong></p>'

        msg = EmailMultiAlternatives(subject, '', from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    else:
        messages.success(request, 'Hakem daha önce onaylanmıştır.')
    try:
        print()
    except:
        messages.warning(request, 'Tekrar deneyiniz.')

    return redirect('sbs:basvuru-referee')

@login_required
def referenceStatus(request, pk):
    reference = ReferenceReferee.objects.get(pk=pk)
    if reference.status == ReferenceReferee.WAITED:
        user = User()
        user.username = reference.email
        user.first_name = reference.first_name
        user.last_name = reference.last_name
        user.email = reference.email
        group = Group.objects.get(name='Hakem')

        user.save()
        user.groups.add(group)
        user.is_active = True
        user.save()

        person = Person()
        person.tc = reference.tc
        person.motherName = reference.motherName
        person.fatherName = reference.fatherName
        person.profileImage = reference.profileImage
        person.birthDate = reference.birthDate
        person.bloodType = reference.bloodType
        person.birthplace = reference.birthplace
        if reference.gender == 'Erkek':
            person.gender = Person.MALE
        else:
            person.gender = Person.FEMALE
        person.save()
        communication = Communication()
        communication.postalCode = reference.postalCode
        communication.phoneNumber = reference.phoneNumber
        communication.phoneNumber2 = reference.phoneNumber2
        communication.address = reference.address
        communication.city = reference.city
        communication.country = reference.country
        communication.save()

        judge = Judge(user=user, person=person, communication=communication)
        judge.iban = reference.iban
        judge.save()

        grade = Level(definition=reference.kademe_definition,
                      startDate=reference.kademe_startDate,
                      branch=EnumFields.HALTER.value)
        grade.levelType = EnumFields.LEVELTYPE.GRADE
        grade.status = Level.APPROVED
        grade.isActive = True
        grade.save()

        judge.grades.add(grade)
        judge.save()

        reference.status = ReferenceReferee.APPROVED
        reference.save()

        messages.success(request, 'Hakem Başarıyla Eklenmiştir')

        fdk = Forgot(user=user, status=False)
        fdk.save()
        print(fdk)

        html_content = ''
        subject, from_email, to = 'Bilgi Sistemi Kullanıcı Bilgileri', 'no-reply@halter.gov.tr', user.email
        html_content = '<h2>TÜRKİYE HALTER FEDERASYONU BİLGİ SİSTEMİ</h2>'
        html_content = html_content + '<p><strong>Kullanıcı Adınız :' + str(fdk.user.username) + '</strong></p>'
        html_content = html_content + '<p> <strong>Site adresi:</strong> <a href="https://sbs.halter.gov.tr:9443/newpassword?query=' + str(
            fdk.uuid) + '">https://sbs.halter.gov.tr:9443/sbs/profil-guncelle/?query=' + str(fdk.uuid) + '</p></a>'
        msg = EmailMultiAlternatives(subject, '', from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
    else:
        messages.success(request, 'Hakem daha önce onaylanmıştır.')
    try:
        print()
    except:
        messages.warning(request, 'Tekrar deneyiniz.')

    return redirect('sbs:basvuru-referee')






@login_required
def visaSeminar_onayla(request, pk):
    seminar = VisaSeminar.objects.get(pk=pk)

    if seminar.status == VisaSeminar.WAITED:

        for item in seminar.referee.all():
            visa = Level(dekont='Federasyon', branch=seminar.branch)
            visa.startDate = date(int(seminar.year), 1, 1)
            visa.definition = CategoryItem.objects.get(forWhichClazz='VISA')
            visa.levelType = EnumFields.LEVELTYPE.VISA
            visa.status = Level.APPROVED
            visa.isActive = True
            visa.save()
            for referee in item.visa.all():
                if referee.branch == visa.branch:
                    referee.isActive = False
                    referee.save()
            item.visa.add(visa)
            item.save()
        seminar.status = VisaSeminar.APPROVED
        seminar.save()
    else:
        messages.warning(request, 'Seminer Daha Önce Onaylanmistir.')

    return redirect('sbs:hakem-seminar-duzenle', pk=pk)


@login_required
def kademe_list(request):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')

    coa = []
    for item in CategoryItem.objects.filter(forWhichClazz='REFEREE_GRADE'):
        coa.append(item.pk)
    grade = Level.objects.filter(definition_id__in=coa, levelType=EnumFields.LEVELTYPE.GRADE).distinct()
    return render(request, 'hakem/hakem-KademeListesi.html',
                  {'belts': grade})


@login_required
def kademe_onayla(request, referee_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    grade = Level.objects.get(pk=referee_pk)
    Judge = grade.Judgegrades.first()
    try:
        for item in Judge.grades.all():
            if item.branch == grade.branch:
                item.isActive = False
                item.save()
        grade.status = Level.APPROVED
        grade.isActive = True
        grade.save()
        messages.success(request, 'Kademe   Onaylanmıştır')
    except:
        messages.warning(request, 'Lütfen yeniden deneyiniz.')

    return redirect('sbs:hakem-kademe-listesi')


@login_required
def kademe_reddet_liste(request, referee_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    grade = Level.objects.get(pk=referee_pk)
    grade.status = Level.DENIED
    grade.save()
    messages.success(request, 'Kademe  Reddedilmiştir.')
    return redirect('sbs:hakem-kademe-listesi')


def kademe_onay_hepsi(request):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    coa = []
    for item in CategoryItem.objects.filter(forWhichClazz='REFEREE_GRADE'):
        coa.append(item.pk)
    Belt = Level.objects.filter(definition_id__in=coa, levelType=EnumFields.LEVELTYPE.GRADE, status="Beklemede")

    for grade in Belt:
        coach = grade.Judgegrades.first()
        try:
            for item in coach.grades.all():
                if item.branch == grade.branch:
                    item.isActive = False
                    item.save()
            grade.status = Level.APPROVED
            grade.isActive = True
            grade.save()
            messages.success(request, 'Beklemede olan Kademeler Onaylanmıştır')
        except:
            messages.warning(request, 'Lütfen yeniden deneyiniz.')

    return redirect('sbs:hakem-kademe-listesi')


@login_required
def kademe_reddet_hepsi(request):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    coa = []
    for item in CategoryItem.objects.filter(forWhichClazz='REFEREE_GRADE'):
        coa.append(item.pk)
    Belt = Level.objects.filter(definition_id__in=coa, levelType=EnumFields.LEVELTYPE.GRADE, status="Beklemede")
    for belt in Belt:
        belt.status = Level.DENIED
        belt.save()
    messages.success(request, 'Beklemede olan kademeler   Onaylanmıştır')
    return redirect('sbs:hakem-kademe-listesi')


@login_required
def vize_list(request):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    coa = []
    for item in CategoryItem.objects.filter(forWhichClazz='VISA'):
        coa.append(item.pk)
    grade = Level.objects.filter(definition_id__in=coa, levelType=EnumFields.VISA).distinct()
    return render(request, 'hakem/hakem-Vize-Listesi.html',
                  {'belts': grade})


@login_required
def vize_onayla_liste(request, referee_pk):
    try:
        perm = general_methods.control_access(request)

        if not perm:
            logout(request)
            return redirect('accounts:login')
        visa = Level.objects.get(pk=referee_pk)
        visa.status = Level.APPROVED
        refere = visa.Judgevisa.first()
        for item in refere.visa.all():
            if item.branch == visa.branch:
                item.isActive = False
                item.save()
        visa.isActive = True
        visa.save()
        messages.success(request, 'Vize Onaylanmıştır.')
    except:
        messages.warning(request, 'Yeniden deneyiniz.')

    return redirect('sbs:hakem-vize-listesi')


@login_required
def vize_reddet_liste(request, referee_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    visa = Level.objects.get(pk=referee_pk)
    visa.status = Level.DENIED
    visa.save()
    messages.success(request, 'Vize reddedilmistir.')
    return redirect('sbs:hakem-vize-listesi')



@login_required
def return_visaSeminar_Basvuru(request):
    perm = general_methods.control_access_judge(request)
    if not perm:
        logout(request)
        return redirect('accounts:login')
    user = request.user
    basvurularim=JudgeApplication.objects.none()
    judge=Judge.objects.get(user=user)
    if request.user.groups.filter(name='Hakem').exists():
        seminar = VisaSeminar.objects.filter(judgeApplication__judge__user=user).filter(
            forWhichClazz='REFEREE').distinct()
        basvurularim = JudgeApplication.objects.filter(judge__user=user)

    else:
        seminar = VisaSeminar.objects.filter(forWhichClazz='REFEREE')

    return render(request, 'hakem/VisaSeminar.html', {'seminer': seminar,
                                                                    'basvuru': basvurularim,
                                                                    'user': user,
                                                      'judge':judge})


@login_required
def visaSeminar_Delete_Judge_application(request, pk, competition):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():
        coachApplication = JudgeApplication.objects.get(pk=pk)
        coachApplication.status = JudgeApplication.DENIED
        coachApplication.save()

        seminer = VisaSeminar.objects.get(pk=competition)

        html_content = ''
        subject, from_email, to = 'THF Bilgi Sistemi', 'no-reply@halter.gov.tr', coachApplication.judge.user.email
        html_content = '<h2>TÜRKİYE HALTER FEDERASYONU BİLGİ SİSTEMİ</h2>'
        html_content = '<p><strong>' + str(seminer.name) + '</strong> Seminer  başvurunuz reddedilmiştir.</p>'

        msg = EmailMultiAlternatives(subject, '', from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        log = str(seminer.name) + "    seminer basvusu reddedilmiştir    " + str(
            coachApplication.judge.user.get_full_name())
        log = general_methods.logwrite(request, request.user, log)

        try:
            print()

            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})

    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})


@login_required
def visaSeminar_Onayla_Judge_application(request, pk, competition):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():


            application = JudgeApplication.objects.get(pk=pk)
            seminer = VisaSeminar.objects.get(pk=competition)
            seminer.referee.add(application.judge)
            seminer.save()
            application.status = JudgeApplication.APPROVED
            application.save()

            html_content = ''
            subject, from_email, to = 'THF Bilgi Sistemi', 'no-reply@halter.gov.tr', application.judge.user.email
            html_content = '<h2>TÜRKİYE HALTER FEDERASYONU BİLGİ SİSTEMİ</h2>'
            html_content = '<p><strong>' + str(seminer.name) + '</strong> Seminer  başvurunuz onaylanmıştır.</p>'

            msg = EmailMultiAlternatives(subject, '', from_email, [to])
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            log = str(seminer.name) + "    seminer basvusu onaylanmıştır    " + str(
                application.judge.user.get_full_name())
            log = general_methods.logwrite(request, request.user, log)
            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})


    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})





@login_required
def document(request, pk):
    coach=Judge.objects.get(pk=pk)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="ProjeTakip.pdf"'
    buffer = BytesIO()
    c = canvas.Canvas(buffer)
    c.setTitle('Hakem Belge')

    logo = ImageReader(settings.MEDIA_ROOT+'/hakembelge.png')
    c.drawImage(logo, 0, 0, width=600, height=850, mask='auto')


    c.setFont("Times-Roman",32)

    c.rotate(90)
    # change color
    # c.setFillColorRGB(0, 0, 0.77)
    # say hello (note after rotate the y coord ne
    c.drawString(270,-310, coach.user.get_full_name())


    c.showPage()

    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response