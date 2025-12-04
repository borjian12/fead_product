from django.urls import path
from . import views

app_name = 'auth_app'

urlpatterns = [
    # احراز هویت عمومی
    path('register/seller/', views.SellerRegisterView.as_view(), name='register-seller'),
    path('register/agent/', views.AgentRegisterView.as_view(), name='register-agent'),
    path('admin/create/', views.AdminCreateView.as_view(), name='admin-create'),
    path('telegram/auth/', views.TelegramAuthView.as_view(), name='telegram-auth'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('verify/', views.VerifyEmailView.as_view(), name='verify'),
    path('verify/resend/', views.ResendVerificationView.as_view(), name='resend-verification'),

    # پروفایل کاربری
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/update/', views.UpdateProfileView.as_view(), name='update-profile'),

    # مدیریت کاربران (ادمین)
    path('admin/users/', views.AdminUsersView.as_view(), name='admin-users'),
    path('admin/sellers/<int:seller_id>/approve/', views.ApproveSellerView.as_view(), name='approve-seller'),
    path('admin/agents/<int:agent_id>/approve/', views.ApproveAgentView.as_view(), name='approve-agent'),
    path('admin/sellers/assign/', views.AssignSellerToAgentView.as_view(), name='assign-seller-to-agent'),
    path('admin/buyers/create/', views.CreateBuyerByAdminView.as_view(), name='create-buyer'),
    path('admin/buyers/<int:buyer_id>/approve/', views.ApproveBuyerView.as_view(), name='approve-buyer'),

    # مدیریت نمایندگان
    path('agent/sellers/', views.AgentSellersView.as_view(), name='agent-sellers'),
    path('agent/buyers/', views.AgentBuyersView.as_view(), name='agent-buyers'),

    # آمار
    path('stats/', views.StatsView.as_view(), name='stats'),

    # توکن
    path('token/refresh/', views.CustomTokenRefreshView.as_view(), name='token-refresh'),
]