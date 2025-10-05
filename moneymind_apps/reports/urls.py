from django.urls import path
from .views import *

urlpatterns = [
    path('expenses-by-category/', ExpensesByCategoryView.as_view(), name='expenses-by-category'),
    path('expenses-by-parent-category/', ExpensesByParentCategoryView.as_view(), name='expenses-by-parent-category'),
    path('essential-vs-non-essential/', EssentialVsNonEssentialExpensesView.as_view(), name='essential-vs-non-essential'),
]