from itertools import combinations, product

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from sbs.Forms.CompetitionForm import CompetitionForm
from sbs.Forms.CompetitionSearchForm import CompetitionSearchForm
from django.db.models import Q
from sbs.models import SportClubUser, SportsClub, Competition, Athlete, CompAthlete, Weight, CompCategory, Coach
from sbs.models.SimpleCategory import SimpleCategory
from sbs.models.EnumFields import EnumFields
from sbs.models.SandaAthlete import SandaAthlete
from sbs.models.TaoluAthlete import TaoluAthlete
from sbs.services import general_methods
from sbs.Forms.SimplecategoryForm import SimplecategoryForm

from datetime import date,datetime
from django.utils import timezone


@login_required
def categori_ekle(request):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    simplecategoryForm = SimplecategoryForm()
    categoryitem = SimpleCategory.objects.all()
    if request.method == 'POST':
        simplecategoryForm = SimplecategoryForm(request.POST)
        if simplecategoryForm.is_valid():
            simplecategoryForm.save()
            messages.success(request, 'Kategori Başarıyla Güncellenmiştir.')
        else:
            messages.warning(request, 'Birşeyler ters gitti yeniden deneyiniz.')

    return render(request, 'musabaka/müsabaka-Simplecategori.html',
                  {'category_item_form': simplecategoryForm, 'categoryitem': categoryitem})


@login_required
def aplication(request, pk):
    perm = general_methods.control_access_klup(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')


    musabaka = Competition.objects.get(pk=pk)

    login_user = request.user
    user = User.objects.get(pk=login_user.pk)
    weights = Weight.objects.all()
    if user.groups.filter(name='KulupUye'):
        sc_user = SportClubUser.objects.get(user=user)
        if sc_user.dataAccessControl == True:
            if user.groups.filter(name='KulupUye'):
                clubsPk = []
                clubs = SportsClub.objects.filter(clubUser=sc_user)
                for club in clubs:
                    clubsPk.append(club.pk)

                comAthlete = CompAthlete.objects.filter(competition=pk,
                                                        athlete__licenses__sportsClub__in=clubsPk).distinct()


        else:
            messages.warning(request, 'Lütfen Eksik olan Sporcu Bilgilerini tamamlayiniz.')
            return redirect('sbs:musabakalar')
    elif user.groups.filter(name__in=['Yonetim', 'Admin']):
        comAthlete = CompAthlete.objects.filter(competition=pk).distinct()

    elif user.groups.filter(name='Antrenor'):
        coach = Coach.objects.get(user=user)
        comAthlete = CompAthlete.objects.filter(competition=pk, athlete__licenses__coach=coach).distinct()
    return render(request, 'musabaka/basvuru.html',
                  {'athletes': comAthlete, 'competition': musabaka, 'weights': weights})




@login_required
def return_competition(request):

    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    competitions = Competition.objects.filter(startDate__year=timezone.now().year)
    year=timezone.now().year
    year=Competition.objects.values('year').distinct().order_by('year')
    return render(request, 'musabaka/sonuclar.html',{'competitions': competitions,'year':year})


@login_required
def return_competitions(request):
    perm = general_methods.control_access_klup(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    comquery=CompetitionSearchForm()
    competition = Competition.objects.filter(registerStartDate__lte=timezone.now(),
                                             registerFinishDate__gte=timezone.now())
    competitions = Competition.objects.none()


    if request.method == 'POST':
        name= request.POST.get('name')
        startDate= request.POST.get('startDate')
        compType= request.POST.get('compType')
        compGeneralType= request.POST.get('compGeneralType')
        if name or startDate or compType or compGeneralType:
            query = Q()
            if name:
                query &= Q(name__icontains=name)
            if startDate:
                query &= Q(year=int(startDate))
            if compType:
                query &= Q(compType__in=compType)
            if compGeneralType:
                query &= Q(compGeneralType__in=compGeneralType)
            competitions=Competition.objects.filter(query).distinct()
        else:
            competitions = Competition.objects.all()
    return render(request, 'musabaka/musabakalar.html',
                  {'competitions': competitions, 'query': comquery, 'application': competition})


@login_required
def musabaka_ekle(request):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    competition_form = CompetitionForm()
    if request.method == 'POST':
        competition_form = CompetitionForm(request.POST)
        if competition_form.is_valid():
            competition_form.save()
            messages.success(request, 'Müsabaka Başarıyla Kaydedilmiştir.')

            return redirect('sbs:musabakalar')
        else:

            messages.warning(request, 'Alanları Kontrol Ediniz')

    return render(request, 'musabaka/musabaka-ekle.html',
                  {'competition_form': competition_form})


@login_required
def musabaka_duzenle(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')

    musabaka = Competition.objects.get(pk=pk)
    athletes = CompAthlete.objects.filter(competition=pk)
    competition_form = CompetitionForm(request.POST or None, instance=musabaka)
    if request.method == 'POST':
        if competition_form.is_valid():
            competition_form.save()
            messages.success(request, 'Müsabaka Başarıyla Güncellenmiştir.')

            return redirect('sbs:musabaka-duzenle', pk=pk)
        else:

            messages.warning(request, 'Alanları Kontrol Ediniz')

    return render(request, 'musabaka/musabaka-duzenle.html',
                  {'competition_form': competition_form, 'competition': musabaka, 'athletes': athletes})


@login_required
def musabaka_sil(request, pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():
        try:
            obj = Competition.objects.get(pk=pk)
            obj.delete()
            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except Competition.DoesNotExist:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})

    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})


def musabaka_sporcu_ekle(request, athlete_pk, competition_pk):
    perm = general_methods.control_access(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')

    if request.method == 'POST':
        compAthlete = CompAthlete()
        compAthlete.athlete = Athlete.objects.get(pk=athlete_pk)
        compAthlete.competition = Competition.objects.get(pk=competition_pk)
        compAthlete.sıklet = Weight.objects.get(pk=request.POST.get('weight'))
        compAthlete.total = request.POST.get('total')
        compAthlete.save()
        messages.success(request, 'Sporcu Eklenmiştir')

    return redirect('sbs:lisans-listesi')


@login_required
def musabaka_sporcu_sec(request, pk):
    perm = general_methods.control_access_klup(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')

    weights = Weight.objects.all()

    competition = Competition.objects.filter(registerStartDate__lte=timezone.now(),
                                             registerFinishDate__gte=timezone.now())

    # login_user = request.user
    # user = User.objects.get(pk=login_user.pk)
    # competition = Competition.objects.get(pk=pk)
    # weights = Weight.objects.all()
    # if user.groups.filter(name='KulupUye'):
    #     sc_user = SportClubUser.objects.get(user=user)
    #     clubsPk = []
    #     clubs = SportsClub.objects.filter(clubUser=sc_user)
    #     for club in clubs:
    #         clubsPk.append(club.pk)
    #     athletes = Athlete.objects.filter(licenses__sportsClub__in=clubsPk).distinct()
    # elif user.groups.filter(name__in=['Yonetim', 'Admin']):
    #     athletes = Athlete.objects.all()

    return render(request, 'musabaka/musabaka-sporcu-sec.html',
                  {'pk': pk, 'weights': weights, 'application': competition})
                  # ,{'athletes': athletes, 'competition': competition, })

@login_required
def return_sporcu(request):
    # print('ben geldim')
    login_user = request.user
    user = User.objects.get(pk=login_user.pk)
    # /datatablesten gelen veri kümesi datatables degiskenine alindi
    if request.method == 'GET':
        datatables = request.GET
        pk = request.GET.get('cmd')
        # print('pk beklenen deger =',pk)
        competition = Competition.objects.get(pk=pk)
        # kategori = CompetitionCategori.objects.get(pk=request.GET.get('cmd'))

    elif request.method == 'POST':
        datatables = request.POST
        # print(datatables)
        # print("post islemi gerceklesti")

    # /Sayfanın baska bir yerden istenmesi durumunda degerlerin None dönmemesi icin degerler try boklari icerisine alindi
    try:
        draw = int(datatables.get('draw'))
        # print("draw degeri =", draw)
        # Ambil start
        start = int(datatables.get('start'))
        # print("start degeri =", start)
        # Ambil length (limit)
        length = int(datatables.get('length'))
        # print("lenght  degeri =", length)
        # Ambil data search
        search = datatables.get('search[value]')
        # print("search degeri =", search)
    except:
        draw = 1
        start = 0
        length = 10

    if length == -1:
        if user.groups.filter(name='KulupUye'):
            sc_user = SportClubUser.objects.get(user=user)
            clubsPk = []
            clubs = SportsClub.objects.filter(clubUser=sc_user)
            for club in clubs:
                clubsPk.append(club.pk)

            modeldata = Athlete.objects.filter(licenses__sportsClub__in=clubsPk).distinct()
            total = modeldata.count()

        elif user.groups.filter(name__in=['Yonetim', 'Admin']):
            modeldata = Athlete.objects.all()
            total = Athlete.objects.all().count()


    else:
        if search:
            modeldata =Athlete.objects.filter(
                Q(user__last_name__icontains=search) | Q(user__first_name__icontains=search) | Q(
                    user__email__icontains=search))
            total = modeldata.count();

        else:
            compAthlete=CompAthlete.objects.filter(competition=competition)
            athletes = []
            for comp in compAthlete:
                if comp.athlete:
                        athletes.append(comp.athlete.pk)
            if user.groups.filter(name='KulupUye'):
                sc_user = SportClubUser.objects.get(user=user)
                clubsPk = []
                clubs = SportsClub.objects.filter(clubUser=sc_user)
                for club in clubs:
                    clubsPk.append(club.pk)
                modeldata = Athlete.objects.exclude(pk__in=athletes).filter(licenses__sportsClub__in=clubsPk).distinct()[start:start + length]
                total = Athlete.objects.exclude(pk__in=athletes).filter(
                    licenses__sportsClub__in=clubsPk).distinct().count()
            elif user.groups.filter(name__in=['Yonetim', 'Admin']):
                modeldata = Athlete.objects.exclude(pk__in=athletes)[start:start + length]
                total = Athlete.objects.exclude(pk__in=athletes).distinct().count()
            elif user.groups.filter(name='Antrenor'):
                modeldata = Athlete.objects.filter(licenses__coach__user=user).exclude(pk__in=athletes).distinct()[
                            start:start + length]

                total = Athlete.objects.filter(licenses__coach__user=user).exclude(pk__in=athletes).distinct().count()




    say = start + 1
    start = start + length
    page = start / length

    beka = []
    for item in modeldata:
        klup=''
        try:
            if item.licenses:
                for lisans in item.licenses.all():
                    if lisans.sportsClub:
                        klup = str(lisans.sportsClub) + "<br>" + klup
        except:
            klup=''
        if item.person.birthDate is not None:
            date = item.person.birthDate.strftime('%d/%m/%Y')
        else:
            date = ''
        data = {
            'say': say,
            'pk': item.pk,

            'name': item.user.first_name + ' ' + item.user.last_name,

            'birthDate': date,

            'klup':klup,

        }
        beka.append(data)
        say += 1


    response = {

        'data': beka,
        'draw': draw,
        'recordsTotal': total,
        'recordsFiltered': total,

    }
    return JsonResponse(response)


@login_required
def update_athlete(request, pk, competition):
    perm = general_methods.control_access_klup(request)
    login_user = request.user

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():

        try:
            user = User.objects.get(pk=login_user.pk)
            compAthlete = CompAthlete.objects.get(pk=competition)
            total = request.POST.get('total')
            siklet = request.POST.get('weight')
            if total is not None:
                compAthlete.total = total
            if siklet is not None:
                compAthlete.sıklet = Weight.objects.get(pk=siklet)
            compAthlete.save()

            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except SandaAthlete.DoesNotExist:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})

    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})







@login_required
def choose_athlete(request, pk, competition):
    perm = general_methods.control_access_klup(request)
    login_user = request.user

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():



        try:
            user = User.objects.get(pk=login_user.pk)
            competition = Competition.objects.get(pk=competition)
            athlete = Athlete.objects.get(pk=pk)
            compAthlete = CompAthlete()
            compAthlete.athlete = athlete
            compAthlete.competition = competition
            compAthlete.total = request.POST.get('total')
            compAthlete.sıklet = Weight.objects.get(pk=request.POST.get('weight'))
            compAthlete.save()


            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except SandaAthlete.DoesNotExist:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})

    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})











@login_required
def musabaka_sporcu_tamamla(request, athletes):
    perm = general_methods.control_access(request)
    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST':
        athletes1 = request.POST.getlist('selected_options')
        if athletes1:
            return redirect('sbs:musabaka-sporcu-tamamla', athletes=athletes1)
            # for x in athletes1:
            #
            #         athlete = Athlete.objects.get(pk=x)
            #         compAthlete = CompAthlete()
            #         compAthlete.athlete = athlete
            #         compAthlete.competition = competition
            #         compAthlete.save()
        else:
            messages.warning(request, 'Sporcu Seçiniz')

    return render(request, 'musabaka/musabaka-sonuclar.html', {'athletes': athletes})


@login_required
def musabaka_sporcu_sil(request, pk):
    perm = general_methods.control_access_klup(request)

    if not perm:
        logout(request)
        return redirect('accounts:login')
    if request.method == 'POST' and request.is_ajax():
        try:
            athlete = CompAthlete.objects.get(pk=pk)
            athlete.delete()
            return JsonResponse({'status': 'Success', 'messages': 'save successfully'})
        except SandaAthlete.DoesNotExist:
            return JsonResponse({'status': 'Fail', 'msg': 'Object does not exist'})

    else:
        return JsonResponse({'status': 'Fail', 'msg': 'Not a valid request'})



@login_required
def result_list(request, pk):
    perm = general_methods.control_access_klup(request)
    if not perm:
        logout(request)
        return redirect('accounts:login')
    competition = Competition.objects.filter(pk=pk)

    compAthlete = CompAthlete.objects.filter(competition=pk).order_by('degree')
    compCategory = CompCategory.objects.filter(competition=pk).order_by('-name')
    print(compAthlete)
    print(compCategory)
    for item in compAthlete:
        print(item.pk)
        print(item.compcategory)
        print(item.athlete.user.get_full_name())

    return render(request, 'musabaka/musabaka-sonuclar.html',
                  {'compCategory': compCategory, 'compAthlete': compAthlete})



@login_required
def return_competition_ajax(request):
    # print('ben geldim')
    login_user = request.user
    user = User.objects.get(pk=login_user.pk)
    # /datatablesten gelen veri kümesi datatables degiskenine alindi
    if request.method == 'GET':
        datatables = request.GET
        pk = request.GET.get('cmd').strip()

    elif request.method == 'POST':
        datatables = request.POST
        # print(datatables)
        # print("post islemi gerceklesti")

    # /Sayfanın baska bir yerden istenmesi durumunda degerlerin None dönmemesi icin degerler try boklari icerisine alindi
    try:
        draw = int(datatables.get('draw'))
        # print("draw degeri =", draw)
        # Ambil start
        start = int(datatables.get('start'))
        # print("start degeri =", start)
        # Ambil length (limit)
        length = int(datatables.get('length'))
        # print("lenght  degeri =", length)
        # Ambil data search
        search = datatables.get('search[value]')
        # print("search degeri =", search)
    except:
        draw = 1
        start = 0
        length = 10
    modeldata=Competition.objects.none()
    if length == -1:
        print()

        # if user.groups.filter(name='KulupUye'):
        #     sc_user = SportClubUser.objects.get(user=user)
        #     clubsPk = []
        #     clubs = SportsClub.objects.filter(clubUser=sc_user)
        #     for club in clubs:
        #         clubsPk.append(club.pk)
        #
        #     modeldata = Athlete.objects.filter(licenses__sportsClub__in=clubsPk).distinct()
        #     total = modeldata.count()
        #
        # elif user.groups.filter(name__in=['Yonetim', 'Admin']):
        #     modeldata = Athlete.objects.all()
        #     total = Athlete.objects.all().count()


    else:
        if search:
            modeldata =Competition.objects.filter(
                Q(name=search))
            total = modeldata.count();

        else:
            # compAthlete=CompAthlete.objects.filter(competition=competition)
            # athletes = []
            # for comp in compAthlete:
            #     if comp.athlete:
            #             athletes.append(comp.athlete.pk)
            if user.groups.filter(name='KulupUye'):
                print('klüp üye ')
                # sc_user = SportClubUser.objects.get(user=user)
                # clubsPk = []
                # clubs = SportsClub.objects.filter(clubUser=sc_user)
                # for club in clubs:
                #     clubsPk.append(club.pk)
                # modeldata = Athlete.objects.exclude(pk__in=athletes).filter(licenses__sportsClub__in=clubsPk).distinct()[start:start + length]
                # total = mAthlete.objects.exclude(pk__in=athletes).filter(licenses__sportsClub__in=clubsPk).distinct().count()
            elif user.groups.filter(name__in=['Yonetim', 'Admin']):

                modeldata = Competition.objects.filter(year=pk)
                total =modeldata.count()


    say = start + 1
    start = start + length
    page = start / length

    beka = []
    for item in modeldata:
        data = {
            'say': say,
            'pk': item.pk,
            'name': item.name,

        }
        beka.append(data)
        say += 1

    response = {

        'data': beka,
        'draw': draw,
        'recordsTotal': total,
        'recordsFiltered': total,

    }
    return JsonResponse(response)
