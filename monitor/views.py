import re
from datetime import datetime, time
import json
import logging
import requests
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.timezone import localtime, make_aware, is_naive
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .forms import LoginForm, RegisterForm
from .models import ParentUser, BrowsingLog, RiskAlert
from .utils.alert_engine import send_parent_alert
from .utils.nsfw_detector import get_nsfw_score
from .utils.predict_behaviour import predict_behavior

logger = logging.getLogger(__name__)

# ------------------------ Root Redirect ------------------------

def home_redirect(request):
    if not request.session.get('user_email'):
        return redirect('register')
    parent_email = request.session.get('user_email')
    try:
        parent = ParentUser.objects.get(email=parent_email)
        children = parent.children
        if not children:
            return redirect('dashboard')
        elif len(children) == 1:
            request.session['child_email'] = children[0]
            return redirect('dashboard')
        else:
            return redirect('select_child')
    except ParentUser.DoesNotExist:
        return redirect('register')

# ------------------------ Auth Views ------------------------

def register_user(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            child_emails = form.cleaned_data['child_emails']  # Already a list

            if ParentUser.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
            else:
                ParentUser.objects.create_user(
                    full_name=form.cleaned_data['full_name'],
                    email=email,
                    password=form.cleaned_data['password'],
                    children=child_emails
                )
                messages.success(request, "Registration successful. Please log in.")
                return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def login_user(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = ParentUser.objects.get(email=email)
                if check_password(password, user.password):
                    request.session['user_email'] = user.email
                    request.session['user_name'] = user.full_name
                    request.session['children'] = user.children
                    if len(user.children) == 1:
                        request.session['child_email'] = user.children[0]
                        return redirect('dashboard')
                    return redirect('select_child')
                else:
                    messages.error(request, "Incorrect password.")
            except ParentUser.DoesNotExist:
                messages.error(request, "User not found.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_user(request):
    logout(request)
    request.session.flush()
    return redirect('login')

# ------------------------ Child Selection ------------------------

def select_child(request):
    if 'user_email' not in request.session:
        return redirect('login')
    try:
        parent = ParentUser.objects.get(email=request.session['user_email'])
        return render(request, 'select_child.html', {'children': parent.children})
    except ParentUser.DoesNotExist:
        return redirect('login')

def set_child(request):
    if request.method == 'POST':
        selected = request.POST.get("child_email")
        request.session["child_email"] = selected
        return redirect("dashboard")
    return redirect('select_child')


@require_POST
def switch_child(request):
    selected_child = request.POST.get('child_email')
    if selected_child:
        request.session['child_email'] = selected_child
    return redirect('dashboard')

# ------------------------ Dashboard ------------------------

def dashboard(request):
    user_email = request.session.get('user_email')
    selected_child = request.session.get('child_email')

    if not user_email:
        messages.error(request, "Please log in first.")
        return redirect('login')

    if not selected_child:
        # ❗ Avoid flash by redirecting immediately before any render happens
        return redirect('select_child')

    try:
        user = ParentUser.objects.get(email=user_email)
    except ParentUser.DoesNotExist:
        messages.error(request, "User not found. Please register.")
        return redirect('register')

    logs = BrowsingLog.objects.filter(child_email=selected_child).order_by('-timestamp')

    for log in logs:
        if log.timestamp and is_naive(log.timestamp):
            log.timestamp = make_aware(log.timestamp)
        log.timestamp = localtime(log.timestamp)

    safe_logs = [log for log in logs if log.label.lower() == "safe"]
    risky_logs = [log for log in logs if log.label.lower() == "risky"]

    return render(request, 'dashboard.html', {
        'logs': logs[:50],
        'safe_count': len(safe_logs),
        'risky_count': len(risky_logs),
        'user_email': user_email,
        'children': user.children,
        'selected_child': selected_child
    })

# ------------------------ Alerts ------------------------

def view_alerts(request):
    if 'user_email' not in request.session:
        return redirect('login')

    alerts = RiskAlert.objects.filter(
        parent_email=request.session['user_email']
    ).order_by('-triggered_at')[:50]

    return render(request, 'view_alerts.html', {'alerts': alerts})

# ------------------------ Browsing Log API ------------------------
import traceback
from django.utils.timezone import now
from datetime import timedelta

@csrf_exempt
def log_browsing_data(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        logger.info(f"Received data: {data}")

        required_fields = ["child_email", "url", "title", "query", "image_score", "duration_sec", "hour_of_day"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return JsonResponse({"error": f"Missing fields: {', '.join(missing)}"}, status=400)

        query = data["query"].strip() or data["title"]
        url = data["url"]
        child_email = data["child_email"]
        hour = data["hour_of_day"]
        duration_sec = data["duration_sec"]
        normalized_url = normalize_youtube_url(url)
        MIN_DURATION_UPDATE_WINDOW = 3600  # seconds
        MIN_TOTAL_DURATION_FOR_NEW_LOG = 60  # seconds

        existing_log = BrowsingLog.objects.filter(
            child_email=child_email,
            url=normalized_url,
            timestamp__gte=now() - timedelta(minutes=30)
        ).order_by('-timestamp').first()

        if existing_log:
            if duration_sec < MIN_DURATION_UPDATE_WINDOW:
                # Ignore very short intervals to reduce noise
                logger.info(f"Ignoring very short duration log for {normalized_url}")
                return JsonResponse({"status": "ignored short duration log"}, status=200)

            existing_log.duration_sec += duration_sec
            existing_log.timestamp = now()
            existing_log.save()

            # If after update total duration is still under threshold, don't analyze again
            if existing_log.duration_sec < MIN_TOTAL_DURATION_FOR_NEW_LOG:
                logger.info(f"♻️ Updated existing log (total {existing_log.duration_sec}s), skipping re-analysis")
                return JsonResponse({"status": "updated existing log"}, status=200)

        # Skip homepage URLs
        HOMEPAGE_DOMAINS_TO_SKIP = [
            "https://www.youtube.com/",
            "https://youtube.com/",
            "https://www.google.com/",
            "https://google.com/",
            "https://www.facebook.com/",
            "https://facebook.com/",
            "https://www.instagram.com/",
            "https://instagram.com/",
            "https://www.twitter.com/",
            "https://twitter.com/",
            "https://chatgpt.com/",
        ]

        if any(url.rstrip('/') == domain.rstrip('/') for domain in HOMEPAGE_DOMAINS_TO_SKIP):
            logger.info(f"Skipping homepage URL: {url}")
            return JsonResponse({"status": "skipped homepage url"}, status=200)

        if "youtube.com" in url or "youtu.be" in url:
            video_id = get_youtube_video_id(url)
            if not video_id:
                logger.info(f"Skipping non-video YouTube URL: {url}")
                return JsonResponse({"status": "skipped non-video youtube url"}, status=200)

        if "google.com" in url and "/search" not in url:
            logger.info(f"Skipping non-search Google URL: {url}")
            return JsonResponse({"status": "skipped non-search google url"}, status=200)

        # Fresh analysis
        image_score = 0.0
        if "youtube.com" in url or "youtu.be" in url:
            image_score = fetch_and_analyze_thumbnail(url) or data.get("image_score", 0.0)
        else:
            if os.path.exists(url):
                image_score = get_nsfw_score(url)
            else:
                logger.info(f"Skipping NSFW check for non-local non-YouTube URL: {url}")

        input_data = {"query": query, "url": normalized_url, "hour": hour}
        result = predict_behavior(input_data)
        logger.info(f" Predict result: {result} ({type(result)})")

        label = result.get("verdict", "safe")
        reason = result.get("reason", "")
        summary = result.get("summary", "")

        parent = None
        for p in ParentUser.objects.all():
            if child_email in p.children:
                parent = p
                break

        if not parent:
            return JsonResponse({"error": "No parent found for this child"}, status=404)

        if label == "safe" and image_score >= 0.7:
            logger.info("LLM verdict is safe, but NSFW score high. Respecting LLM verdict.")
            summary += f" (NSFW score: {image_score})"
        elif label in ["risky", "partial_risky"] and image_score >= 0.7:
            reason = "NSFW thumbnail detected"
            summary += f"\nThumbnail NSFW score: {image_score}"

        log = BrowsingLog.objects.create(
            child_email=child_email,
            parent_email=parent.email,
            title=data["title"],
            url=normalized_url,
            query=query if image_score < 0.7 else "Thumbnail detected as inappropriate",
            duration_sec=duration_sec,
            is_night_time=hour >= 22 or hour <= 6,
            label=label,
            reason=reason,
            summary=summary,
            email_sent=False
        )

        if label == "risky" and not log.email_sent:
            send_parent_alert(log, nsfw_thumbnail_score=image_score if image_score >= 0.7 else None)
            log.email_sent = True
            log.save()

        return JsonResponse({"status": "success"})

    except Exception as e:
        logger.error("Unexpected error in log_browsing_data:")
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)

# ------------------------ Child Email API ------------------------

@csrf_exempt
def validate_child_email(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Only POST allowed"}, status=405)

        data = json.loads(request.body)
        email = data.get("email")

        if not email:
            logger.warning("Child email missing from request")
            return JsonResponse({"error": "Email field is required"}, status=400)

        logger.info(f" Validating child email: {email}")

        # Manual lookup to bypass unsupported __contains
        all_parents = ParentUser.objects.all()
        for parent in all_parents:
            if email in parent.children:
                logger.info(f" Child email {email} found under parent {parent.email}")
                return JsonResponse({"valid": True, "parent_email": parent.email})

        logger.warning(f" Child email {email} not found")
        return JsonResponse({"valid": False}, status=404)

    except Exception as e:
        logger.exception(" Internal Server Error during child email validation")
        return JsonResponse({"error": str(e)}, status=500)


# ------------------------ Helpers ------------------------
from django.utils.timezone import now

def normalize_youtube_url(url):
    video_id = get_youtube_video_id(url)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url

def is_duplicate_log(email, url):
    normalized_url = normalize_youtube_url(url)

    now_time = now()
    start_of_day = datetime.combine(now_time.date(), time.min)
    end_of_day = datetime.combine(now_time.date(), time.max)

    return BrowsingLog.objects.filter(
        child_email=email,
        url=normalized_url,
        timestamp__gte=start_of_day,
        timestamp__lt=end_of_day
    ).first()

def get_youtube_video_id(url):
    patterns = [
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

import tempfile
import os

import os
from django.conf import settings

def fetch_and_analyze_thumbnail(video_url):
    video_id = get_youtube_video_id(video_url)
    if not video_id:
        logger.warning(f"Could not extract video ID from URL: {video_url}")
        return None

    thumbnails_dir = os.path.join(settings.BASE_DIR, "data", "thumbnails")
    os.makedirs(thumbnails_dir, exist_ok=True)

    for quality in ['maxresdefault', 'hqdefault', 'mqdefault', 'default']:
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
        response = requests.get(thumbnail_url)

        if response.status_code == 200:
            try:
                thumbnail_path = os.path.join(thumbnails_dir, f"{video_id}_{quality}.jpg")
                with open(thumbnail_path, "wb") as f:
                    f.write(response.content)

                score = get_nsfw_score(thumbnail_path)
                logger.info(f" NSFW score for {video_id} at {quality}: {score}")
                return score

            except Exception as e:
                logger.error(f" Error analyzing thumbnail for {video_id}: {e}")
                return None
        else:
            logger.info(f"Thumbnail not found at {thumbnail_url}")

    logger.warning(f"No thumbnail available for video ID {video_id}")
    return None

