import kivy
kivy.require('2.2.1')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.clock import Clock
import schedule
import threading
import subprocess
import random
import pandas as pd
import webbrowser
import time as import_time
import os

class NotificationService:
    def __init__(self, name, selected_time):
        self.name = name
        self.selected_time = selected_time
        self.running = True
        self.video_url = None
        self.notification_sent = False
        self.notification_scheduled = False  # New flag to prevent multiple scheduling

    def get_random_quote(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_file_path = os.path.join(script_dir, 'quotes_data.csv')
        df = pd.read_csv(csv_file_path, header=None)
        quote_list = df[0].tolist()
        return random.choice(quote_list)

    def get_random_video_url(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        video_csv_file_path = os.path.join(script_dir, 'morevideos.csv')
        df_videos = pd.read_csv(video_csv_file_path, header=None)
        video_urls = df_videos[0].tolist()
        return random.choice(video_urls)

    def send_notification(self):
        if not self.notification_scheduled:  # Check if a notification is already scheduled
            self.notification_scheduled = True

            message = self.get_random_quote()
            self.video_url = self.get_random_video_url()  # Get a new random video URL each time

            notification_script = f'display notification "{message}" with title "Motivational Quote of the Day" sound name "Crystal"'
            subprocess.run(['osascript', '-e', notification_script])

            dialog_script = f'display dialog "{message}" with title "Motivational Quote of the Day" buttons {{"Watch Video", "OK"}}'
            result = subprocess.run(['osascript', '-e', dialog_script], capture_output=True, text=True)

            print("Notification sent to", self.name)

            if result.returncode == 0 and 'Watch Video' in result.stdout:
                webbrowser.open(self.video_url)

            self.notification_sent = True
            self.notification_scheduled = False # Reset the flag after sending the notification

    def schedule_notifications(self):
        time_parts = self.selected_time.split()
        time = time_parts[0]
        period = time_parts[1].upper()
        hour, minute = map(int, time.split(':'))

        if period == 'PM' and hour < 12:
            hour += 12

        schedule.every().day.at(f'{hour:02d}:{minute:02d}').do(self.send_notification)

        while self.running:
            schedule.run_pending()
            import_time.sleep(1)

    def stop(self):
        self.running = False

class DailyDose(App):
    def __init__(self, **kwargs):
        super(DailyDose, self).__init__(**kwargs)
        self.notification_service = None
        self.watch_video_button = None
        self.image = None
        self.label = None
        self.kivy_running = False  # Flag to track if the Kivy app is running or not

    def build(self):
        layout = BoxLayout(orientation='vertical')
        self.image = Image(source='couch.png')
        layout.add_widget(self.image)

        self.label = Label(text="Welcome!\nThis app is designed to send daily motivational quotes at a specified time of your choice.\nPlease input your preferred time in the format (HH:MM AM/PM).",
                           halign='center', valign='middle')
        layout.add_widget(self.label)

        self.name_input = TextInput(
            multiline=False, hint_text="Please input your name here.",
            halign='center', padding=(50, 10, 50, 10)
        )
        layout.add_widget(self.name_input)

        self.time_input = TextInput(
            multiline=False, hint_text="Enter preferred time (HH:MM AM/PM)",
            halign='center', padding=(50, 10, 50, 10)
        )
        layout.add_widget(self.time_input)

        self.button = Button(text="Submit", on_press=self.on_submit)
        layout.add_widget(self.button)

        self.exit_button = Button(text="Exit", on_press=self.on_exit)
        layout.add_widget(self.exit_button)


        return layout

    def open_video_url(self, instance):
        video_url = instance.video_url
        webbrowser.open(video_url)

    def on_submit(self, instance):
        name = self.name_input.text
        selected_time = self.time_input.text

        if not self.validate_time_input(selected_time):
            self.label.text = "Invalid time format. Please use HH:MM AM/PM format."
            return

        self.label.text = f"Welcome, {name}!\nThis is your chosen notification time: {selected_time}"
        self.name_input.parent.remove_widget(self.name_input)
        self.time_input.parent.remove_widget(self.time_input)
        self.button.parent.remove_widget(self.button)

        self.image.source = 'square.png'

        self.start_notification_service(name, selected_time)

        Clock.schedule_interval(self.check_pending_jobs, 1)

    def start_notification_service(self, name, selected_time):
        self.notification_service = NotificationService(name, selected_time)
        threading.Thread(target=self.notification_service.schedule_notifications).start()

    def stop_notification_service(self):
        if self.notification_service:
            self.notification_service.stop()

    #def stop_app(self, instance):
        #self.stop_notification_service()
        #self.kivy_running = False
        #App.get_running_app().stop()

    def validate_time_input(self, time_string):
        try:
            time_parts = time_string.split()
            if len(time_parts) == 2:
                time = time_parts[0]
                period = time_parts[1].upper()
                hour, minute = map(int, time.split(':'))

                if 1 <= hour <= 12 and 0 <= minute < 60 and (period == 'AM' or period == 'PM'):
                    return True
        except ValueError:
            pass
        return False

    def check_pending_jobs(self, dt):
        schedule.run_pending()
        # Check if the video URL is available and add the "Click Me" button if not already added
        if self.kivy_running and self.notification_service and self.notification_service.video_url and not self.watch_video_button:
            self.watch_video_button = Button(
                text='Click Me',
                markup=True,
                size_hint_y=None,
                height=75,
                on_press=self.open_video_url
            )
            self.root.add_widget(self.watch_video_button)
            setattr(self.watch_video_button, 'video_url', self.notification_service.video_url)  # Store the video URL with the button

        # Check if the notification is sent and update the text and image
        if self.kivy_running and self.notification_service and self.notification_service.notification_sent:
            self.label.text = f"Quote sent. Have an amazing day, {self.notification_service.name}. You deserve it!"
            self.image.source = 'spongebob.png'

    def on_exit(self, instance):
        self.kivy_running = False
        self.stop_notification_service()
        App.get_running_app().stop()

if __name__ == '__main__':
    app = DailyDose()
    app.kivy_running = True  # Set the flag to indicate that the Kivy app is running
    app.run()



