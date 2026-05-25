import os
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window

# Kivy oynasining asosiy rangi
Window.clearcolor = (0.05, 0.05, 0.07, 1)

class JarvisAndroidApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        
        # Logo Label
        self.label = Label(
            text='[b][color=00d4ff]JARVIS AI[/color][/b]',
            markup=True,
            font_size='40sp',
            size_hint=(1, 0.6)
        )
        
        # Start button
        self.btn_start = Button(
            text='Uyg\'on, Jarvis',
            font_size='25sp',
            size_hint=(1, 0.2),
            background_color=(0, 0.8, 1, 1)
        )
        self.btn_start.bind(on_press=self.on_start)
        
        # Status Label
        self.status = Label(
            text='Holati: Kutmoqda (Standby)',
            font_size='20sp',
            size_hint=(1, 0.2)
        )
        
        layout.add_widget(self.label)
        layout.add_widget(self.status)
        layout.add_widget(self.btn_start)
        return layout
        
    def on_start(self, instance):
        self.status.text = "Ruxsatlar tekshirilmoqda..."
        self.btn_start.text = "Ulanish boshlandi"
        
        try:
            from android.permissions import request_permissions, Permission
            def callback(permissions, results):
                if all(results):
                    self.status.text = "Holati: Jarvis Audio xizmati faol!\n(Tez orada API integratsiyasi ulanadi...)"
                else:
                    self.status.text = "Holati: Ruxsatlar berilmadi! Jarvis ishlolmaydi."
            
            request_permissions([
                Permission.RECORD_AUDIO,
                Permission.SYSTEM_ALERT_WINDOW,
                Permission.INTERNET
            ], callback)
        except Exception as e:
            self.status.text = f"Holati: Ruxsat xatosi yoki bu Android emas.\n{str(e)}"

if __name__ == '__main__':
    JarvisAndroidApp().run()
