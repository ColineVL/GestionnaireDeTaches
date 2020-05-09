from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

from .forms import TaskForm, NewEntryForm, ExportForm, ProjectForm
from .models import *
from .resources import *
from django.http import HttpResponse
from zipfile import ZipFile
import shutil
from .export import *

# Pas une view, c'est une fonction utile
def progress(project):
    # On récupère les tâches au sein du projet
    tasks = Task.objects.filter(project=project)

    # On calcule le taux d'avancement du projet
    # On considère que toutes les tâches ont le même poids
    nb_tasks = 0
    total_progress = 0
    for task in tasks:
        nb_tasks += 1
        total_progress += task.progress

    if nb_tasks == 0:
        return 0

    return total_progress / nb_tasks


@login_required
def accueil(request):
    return render(request, 'taskmanager/accueil.html')


@login_required
def projects(request):
    # On récupère la liste des projets
    list_projects = request.user.project_set.all()
    # Pour chaque projet, on note le nombre de membres et le nombre de tâches
    for pr in list_projects:
        pr.nbMembers = len(pr.members.all())
        pr.nbTasks = len(pr.task_set.all())

        # Taux d'avancement pour chaque projet (avec int on arrondit à l'entier)
        pr.progress = int(progress(pr))

    return render(request, 'taskmanager/projects.html', locals())


@login_required
def project(request, id_project):
    # On récupère le projet demandé
    project_to_display = get_object_or_404(Project, id=id_project)
    # Si l'utilisateur n'est pas dans le projet, on le redirige vers sa page d'accueil
    if not request.user in project_to_display.members.all():
        return redirect('accueil')
    # On récupère la liste des tâches du projet
    list_tasks = Task.objects.filter(project__id=id_project)
    return render(request, 'taskmanager/project.html', locals())


@login_required
def newproject(request):
    # On crée un formulaire pour créer un nouveau projet
    form = ProjectForm(request.POST or None)
    # On crée une variable qui sera utilisée dans le template pour personnaliser le titre
    method = "New"
    if form.is_valid():
        project_formed = form.save()
        # On redirige vers le projet nouvellement créé
        return redirect('project', id_project=project_formed.id)
    return render(request, 'taskmanager/modifyproject.html', locals())


@login_required
def editproject(request, id_project):
    # On récupère le projet à modifier
    project_formed = get_object_or_404(Project, id=id_project)
    list_members = project_formed.members.all()
    # Si l'utilisateur n'est pas dans le projet, on le redirige vers sa page d'accueil
    if not request.user in list_members:
        return redirect('accueil')
    # On crée un form pour modifier le projet demandé
    form = ProjectForm(request.POST or None, instance=project_formed)
    # On crée une variable qui sera utilisée dans le template pour personnaliser le titre
    method = "Edit"
    if form.is_valid():
        form.save()
        # On redirige vers le projet modifié
        return redirect(project, id_project=id_project)
    return render(request, 'taskmanager/modifyproject.html', locals())


@login_required
def task(request, id_task):
    # On récupère la tâche demandée et la liste des entrées du journal
    task_to_display = get_object_or_404(Task, id=id_task)
    list_journal = Journal.objects.filter(task=task_to_display)
    # Si l'utilisateur n'est pas dans le projet, on le redirige vers sa page d'accueil
    if not request.user in task_to_display.project.members.all():
        return redirect('accueil')
    # On crée un fom pour ajouter une entrée au journal
    form = NewEntryForm(request.POST or None)
    if form.is_valid():
        entry = form.cleaned_data['entry']
        journal = Journal(task=task_to_display)
        journal.entry = entry
        # On remplit les autres attributs du journal
        journal.date = datetime.now()
        journal.author = request.user
        # On l'enregistre
        journal.save()
        # On efface l'entrée de l'utilisateur
        form = NewEntryForm()
    return render(request, "taskmanager/task.html", locals())


@login_required
def newtask(request, id_project):
    # On récupère le projet parent et la liste des membres
    project_related = get_object_or_404(Project, id=id_project)
    list_members = project_related.members.all()
    # Si l'utilisateur n'est pas dans le projet, on le redirige vers sa page d'accueil
    if request.user not in list_members:
        return redirect('accueil')
    # On crée un formulaire pour créer une nouvelle tâche
    form = TaskForm(request.POST or None)
    # On crée une variable qui sera utilisée dans le template pour personnaliser le titre
    method = "New"
    if form.is_valid():
        task_formed = form.save(commit=False)
        task_formed.project = project_related
        task_formed.save()
        # On redirige vers la tâche nouvellement créée
        return redirect('task', id_task=task_formed.id)
    return render(request, 'taskmanager/modifytask.html', locals())


@login_required
def edittask(request, id_task):
    # On récupère la tâche à modifier, le projet parent et la liste des membres
    task_formed = get_object_or_404(Task, id=id_task)
    project_related = task_formed.project
    list_members = project_related.members.all()
    # Si l'utilisateur n'est pas dans le projet, on le redirige vers sa page d'accueil
    if not request.user in list_members:
        return redirect('accueil')
    # On crée un form pour modifier la tâche demandée
    form = TaskForm(request.POST or None, instance=task_formed)
    # On crée une variable qui sera utilisée dans le template pour personnaliser le titre
    method = "Edit"
    if form.is_valid():
        form.save()
        # On redirige vers la tâche modifiée
        return redirect(task, id_task=id_task)
    return render(request, 'taskmanager/modifytask.html', locals())


@login_required
def usertasks_all(request):
    list_tasks = request.user.task_set.all()
    return render(request, "taskmanager/usertasks-all.html", locals())


@login_required
def usertasks_done(request):
    # Dans l'argument, mettre le statut qui correspond à une tâche terminé
    list_tasks = request.user.task_set.filter(status__name="Terminée")
    return render(request, "taskmanager/usertasks-done.html", locals())


@login_required
def membersallprojects(request):
    # On récupère tous les projets de l'utilisateur
    list_projects = request.user.project_set.all()
    # On récupère tous les membres de chaque projet
    for pr in list_projects:
        pr.list_members = pr.members.all()
    return render(request, 'taskmanager/membersallprojects.html', locals())


@login_required
def membersbyproject(request, id_project):
    # On récupère le projet demandé
    project_to_display = get_object_or_404(Project, id=id_project)
    # On récupère tous les membres du projet
    list_members = project_to_display.members.all()
    return render(request, 'taskmanager/membersbyproject.html', locals())


@login_required
def activity_all(request):
    # On récupère tous les projets de l'utilisateur
    list_projects = request.user.project_set.all()

    # On récupère les tâches correspondantes
    list_tasks = Task.objects.none()
    for project in list_projects:
        list_tasks = list_tasks.union(project.task_set.all())

    # On récupère toutes les entrées de journal
    list_entries = Journal.objects.none()
    for task in list_tasks:
        list_entries = list_entries.union(task.journal_set.all())
    # Qu'on trie par date décroissante, en prenant les affiche premier
    list_entries = list_entries.order_by('-date')

    # On récupère le paramètre GET affiche
    # Ce paramètre sert à afficher un nombre précis d'entrées
    dict_choices = {
        "5": 5,
        "10": 10,
        "20": 20,
        "100": 100,
        "Toutes": -1
    }
    try:
        affiche = request.GET['affiche' or None]
    except:
        # Par défaut, affiche vaut 5
        affiche = 5

    # Sinon, on prend l'entier correspondant
    affiche = int(affiche)

    # Enfin, on slash la liste des entrées, si affiche ne vaut pas -1
    if affiche > 0:
        list_entries = list_entries[:affiche]

    return render(request, 'taskmanager/activity-all.html', locals())


@login_required
def activity_per_project(request, id_project):
    # On récupère le projet correspondant
    projet = get_object_or_404(Project, id=id_project)

    # On récupère les tâches
    list_tasks = projet.task_set.all()

    # On récupère toutes les entrées de journal
    list_entries = Journal.objects.none()
    for task in list_tasks:
        list_entries = list_entries.union(task.journal_set.all())
    # Qu'on trie par date décroissante
    list_entries = list_entries.order_by('-date')

    # On récupère le paramètre GET affiche
    # Ce paramètre sert à afficher un nombre précis d'entrées
    dict_choices = {
        "5": 5,
        "10": 10,
        "20": 20,
        "100": 100,
        "Toutes": -1
    }
    try:
        affiche = request.GET['affiche' or None]
    except:
        # Par défaut, affiche vaut 5
        affiche = 5

    # Sinon, on prend l'entier correspondant
    affiche = int(affiche)

    # Enfin, on slash la liste des entrées, si affiche ne vaut pas -1
    if affiche > 0:
        list_entries = list_entries[:affiche]

        # TODO afficher depuis telle date ?

    return render(request, 'taskmanager/activity-per-project.html', locals())

  
@login_required
def export_data(request):
    form = ExportForm(request.POST or None,user=request.user)

    if form.is_valid():
        file_type = form.cleaned_data['file_type']
        archive_name = form.cleaned_data['archive_name']
        bool_project = form.cleaned_data['bool_project']
        bool_task = form.cleaned_data['bool_task']
        bool_status = form.cleaned_data['bool_status']
        bool_journal = form.cleaned_data['bool_Journal']
        one_dir_by_project = form.cleaned_data['one_dir_by_project']
        ordered_journal_by_task = form.cleaned_data['ordered_journal_by_task']
        all_projects = form.cleaned_data['all_projects']

        project_set = request.user.project_set.all()
        if  not all_projects:
            projects_name = form.cleaned_data['project']
            project_set = project_set.filter(name__in=projects_name)

        response = HttpResponse('content_type=application/zip')
        zipObj = ZipFile(response, 'w')

        if bool_project:
            create_file(file_type,'projects.'+file_type,project_set, ProjectRessource(),zipObj)
        if bool_status:
            create_file(file_type,'status.'+file_type,Status.objects.all(), StatusResource(),zipObj)
        if bool_task or bool_journal:
            if one_dir_by_project:
                for project in project_set:
                    os.mkdir(project.name)
                    if bool_task:
                        create_file(file_type,project.name+'/task.'+file_type, Task.objects.filter(project=project), TaskResource(),zipObj)
                    if bool_journal:
                        if ordered_journal_by_task:
                            set = Journal.objects.filter(task__in=Task.objects.filter(project=project)).order_by('task')
                        else:
                            set = Journal.objects.filter(task__in=Task.objects.filter(project=project)).order_by('date')
                        create_file(file_type, project.name+'/journal.'+file_type, set,JournalResource(),zipObj)
                    shutil.rmtree(project.name)
            else:
                if bool_task:
                    create_file(file_type,'task.'+file_type, Task.objects.filter(project__in=project_set),TaskResource(),zipObj)
                if bool_journal:
                    create_file(file_type,'journal.'+file_type, Journal.objects.filter(task__in=Task.objects.filter(project__in=project_set)),JournalResource(),zipObj)

        response['Content-Disposition'] = 'attachment; filename="' + archive_name + '.zip"'
        return response

    return render(request, 'taskmanager/export_data.html', locals())
