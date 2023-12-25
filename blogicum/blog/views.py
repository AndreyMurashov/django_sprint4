from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import UpdateView, CreateView, DetailView, ListView, DeleteView
from django.urls import reverse
from .forms import ProfileEditForm, CommentForm, PostForm
from .models import Post, Category, Comment
import datetime

POST_LIMIT = 5
PAGINATOR_COUNT = 10

# Отображение постов


def index(request):
    today = datetime.datetime.now()
    template_name = 'blog/index.html'
    post_list = (Post.objects.filter(pub_date__lte=today,
                                    is_published=True,
                                    category__is_published=True).annotate(comment_count=Count("comment"))
                 .order_by('-pub_date'))
    paginator = Paginator(post_list, PAGINATOR_COUNT)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {'page_obj': page_obj}
    return render(request, template_name, context)

# def post_detail(request, pk):
#     today = datetime.datetime.now()
#     template_name = 'blog/detail.html'
#     try:
#         post = get_object_or_404(Post.objects
#                                  .filter(pub_date__lte=today,
#                                          is_published=True,
#                                          category__is_published=True),
#                                  pk=pk)
#         context = {'post': post}
#         return render(request, template_name, context)
#     except IndexError:
#         return HttpResponseNotFound('<h1>404 Page not found</h1>')


class PostDetailView(DetailView):
    today = datetime.datetime.now()
    model = Post
    template_name = 'blog/detail.html'

    def get_object(self, queryset=None):
        return get_object_or_404(Post.objects.filter(pub_date__lte=self.today,
                                                     is_published=True,
                                                     category__is_published=True), pk=self.kwargs['post_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comment.select_related('author')
        return context


class CategoryPostsListView(ListView):
    today = datetime.datetime.now()
    model = Post
    paginate_by = PAGINATOR_COUNT
    template_name = 'blog/category.html'

    def get_queryset(self):
        # category = get_object_or_404(
        #     Category,
        #     slug=self.kwargs['category_slug'],
        #     is_published=True)

        return (
            Post.objects.select_related('category').filter(category__slug=self.kwargs['category_slug'],
                                                           is_published=True,
                                                           pub_date__lte=self.today)
            .annotate(comment_count=Count("comment"))
            .order_by("-pub_date"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(
            Category.objects.values('id', 'title', 'description'),
            slug=self.kwargs['category_slug'])
        return context


# Действия с постами

class PostCreateView(LoginRequiredMixin, CreateView):
    form_class = PostForm
    model = Post
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("blog:profile", args=[self.request.user])


class PostUpdateView(LoginRequiredMixin, UpdateView):
    form_class = PostForm
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        if self.get_object().author != request.user:
            return redirect('blog:post_detail', pk=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail',
                       kwargs={'pk': self.kwargs['post_id']})


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        if self.get_object().author != request.user:
            return redirect('blog:post_detail', pk=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = PostForm(instance=self.object)
        return context

    def get_success_url(self):
        return reverse("blog:profile", kwargs={"username": self.request.user})


# Действия с комментариями


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = "blog/comment.html"
    post_obj = None
    today = datetime.datetime.now()

    def dispatch(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Post,
                                         pk=kwargs['post_id'],
                                         pub_date__lte=self.today,
                                         is_published=True,
                                         category__is_published=True,
                                         )
        # self.post_obj = self.comment
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = self.comment
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("blog:post_detail",
                       kwargs={'pk': self.kwargs['post_id']})


class CommentUpdateView(UpdateView):
    form_class = CommentForm
    model = Comment
    template_name = "blog/comment.html"
    pk_url_kwarg = "comment_id"

    def dispatch(self, request, *args, **kwargs):
        comment = get_object_or_404(
            Comment,
            pk=kwargs['comment_id'],
        )
        if comment.author != request.user:
            return redirect('blog:post_detail', id=kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("blog:post_detail",
                       kwargs={'post_id': self.kwargs['post_id']})


class CommentDeleteView(DeleteView):
    model = Comment
    template_name = "blog/comment.html"
    pk_url_kwarg = "comment_id"

    def dispatch(self, request, *args, **kwargs):
        comment = get_object_or_404(
            Comment,
            pk=kwargs['comment_id'],
        )
        if comment.author != request.user:
            return redirect('blog:post_detail', id=kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("blog:post_detail",
                       kwargs={'pk': self.kwargs['post_id']})


# Действия с пользователями
def profile(request, username):
    template_name = 'blog/profile.html'
    user = get_object_or_404(User, username=username)
    post_list = Post.objects.all().select_related('author').filter(author__username=username).annotate(comment_count=Count("comment")).order_by('-pub_date')
    paginator = Paginator(post_list, PAGINATOR_COUNT)
    page_obj = paginator.get_page(
        request.GET.get('page')
    )
    context = {
        'page_obj': page_obj,
        'profile': user
    }
    return render(request, template_name, context)

    # class ProfileListView(ListView):
    #     model = Post
    #     paginate_by = POSTS_PER_PAGE
    #     template_name = 'blog/profile.html'
    #
    #     def get_queryset(self):
    #         return (
    #             self.model.objects.select_related('author')
    #             .filter(author__username=self.kwargs['username'])
    #             .annotate(comment_count=Count("comment"))
    #             .order_by("-pub_date"))
    #
    #     def get_context_data(self, **kwargs):
    #         context = super().get_context_data(**kwargs)
    #         context['profile'] = get_object_or_404(
    #             User,
    #             username=self.kwargs['username'])
    #         return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'blog/user.html'
    form_class = ProfileEditForm

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse("blog:profile", args=[self.request.user])
