from django.urls import path
from .views import *

urlpatterns = [
    path('expenses-by-category/', ExpensesByCategoryView.as_view(), name='expenses-by-category'),
    path('expenses-by-parent-category/', ExpensesByParentCategoryView.as_view(), name='expenses-by-parent-category'),
    path('essential-vs-non-essential/', EssentialVsNonEssentialExpensesView.as_view(), name='essential-vs-non-essential'),
    path('monthly-prediction/', MonthlyExpensesPredictionView.as_view(), name='monthly-prediction'),
    path('saving-evolution/', SavingsEvolutionView.as_view(), name='saving-evolution'),
    path('unified-analysis/', UnifiedDashboardAnalyticsView.as_view(), name='unified-analysis'),
    path('dashboard-overview/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('home/dashboard/', HomeDashboardView.as_view(), name='home-dashboard'),
    path('export/', ExportReportView.as_view(), name='export-report'),

]