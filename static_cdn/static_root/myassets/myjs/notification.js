// static/js/notification.js

// درخواست مجوز اعلان
function requestNotificationPermission() {
    if (!("Notification" in window)) {
        console.log("مرورگر از اعلان پشتیبانی نمی‌کند");
        return;
    }

    Notification.requestPermission().then(function(permission) {
        if (permission === "granted") {
            console.log("مجوز اعلان داده شد");
            // ثبت کاربر برای دریافت اعلان
            registerUserForNotifications();
        } else {
            console.log("مجوز اعلان داده نشد");
        }
    });
}

// ثبت کاربر برای دریافت اعلان
function registerUserForNotifications() {
    fetch('/api/notifications/register/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            'browser': navigator.userAgent
        })
    });
}

// ارسال اعلان به کاربر
function sendNotification(title, body, icon, url) {
    if (!("Notification" in window) || Notification.permission !== "granted") {
        return;
    }

    const options = {
        body: body,
        icon: icon || '/static/images/logo.png',
        badge: '/static/images/badge.png',
        vibrate: [200, 100, 200],
        data: {
            url: url || '/dashboard/',
            dateOfArrival: Date.now()
        },
        actions: [
            { action: 'open', title: 'مشاهده' },
            { action: 'dismiss', title: 'بستن' }
        ]
    };

    const notification = new Notification(title, options);

    notification.onclick = function(event) {
        event.preventDefault();
        window.open(this.data.url, '_blank');
        notification.close();
    };
}

// گرفتن CSRF Token
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// چک کردن وظایف جدید هر ۳۰ ثانیه
function checkNewTasks() {
    fetch('/api/notifications/tasks/')
        .then(response => response.json())
        .then(data => {
            if (data.has_new_tasks) {
                sendNotification(
                    'وظیفه جدید!',
                    `${data.task_count} وظیفه جدید برای شما وجود دارد.`,
                    '/static/images/task-icon.png',
                    '/form-flow/my-tasks/'
                );

                // بروزرسانی شمارنده
                updateTaskBadge(data.task_count);
            }
        })
        .catch(error => console.error('Error:', error));
}

// بروزرسانی شمارنده وظایف
function updateTaskBadge(count) {
    const badge = document.getElementById('task-badge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
}

// اجرا در زمان لود صفحه
document.addEventListener('DOMContentLoaded', function() {
    // درخواست مجوز اعلان
    requestNotificationPermission();

    // چک کردن وظایف هر ۳۰ ثانیه
    setInterval(checkNewTasks, 30000);

    // چک کردن وظایف در اولین بار
    checkNewTasks();
});

// برای صفحات خاص (مثل وظایف من)، چک کردن قوی‌تر
if (window.location.pathname.includes('/my-tasks/')) {
    // چک کردن هر ۱۰ ثانیه در صفحه وظایف
    setInterval(checkNewTasks, 10000);
}


// assets/js/notification.js

document.addEventListener('DOMContentLoaded', function() {
    // بروزرسانی شمارنده وظایف در هدر و سایدبار
    function updateTaskBadges(count) {
        // شمارنده هدر
        const headerBadge = document.getElementById('header-task-badge');
        if (headerBadge) {
            if (count > 0) {
                headerBadge.textContent = count;
                headerBadge.style.display = 'inline-block';
            } else {
                headerBadge.style.display = 'none';
            }
        }

        // شمارنده سایدبار (موبایل)
        const mobileBadge = document.getElementById('mobile-task-badge');
        if (mobileBadge) {
            if (count > 0) {
                mobileBadge.textContent = count;
                mobileBadge.style.display = 'inline-block';
            } else {
                mobileBadge.style.display = 'none';
            }
        }

        // شمارنده سایدبار (دسکتاپ)
        const sidebarBadge = document.getElementById('task-badge');
        if (sidebarBadge) {
            if (count > 0) {
                sidebarBadge.textContent = count;
                sidebarBadge.style.display = 'inline-block';
            } else {
                sidebarBadge.style.display = 'none';
            }
        }

        const sidebarBadgeDesktop = document.getElementById('task-badge-desktop');
        if (sidebarBadgeDesktop) {
            if (count > 0) {
                sidebarBadgeDesktop.textContent = count;
                sidebarBadgeDesktop.style.display = 'inline-block';
            } else {
                sidebarBadgeDesktop.style.display = 'none';
            }
        }
    }

    // دریافت تعداد وظایف از API
    function fetchTaskCount() {
        fetch('/form_flow/api/task-count/')
            .then(response => response.json())
            .then(data => {
                updateTaskBadges(data.task_count);
            })
            .catch(error => console.error('Error fetching task count:', error));
    }

    // چک کردن وظایف هر 30 ثانیه
    fetchTaskCount();
    setInterval(fetchTaskCount, 30000);
});