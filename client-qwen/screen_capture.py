"""Explicit Windows region selection; only the chosen image leaves local memory."""
import base64
import io


def encode_region(image,rectangle):
    left,top,right,bottom=rectangle
    if not (0<=left<right<=image.width and 0<=top<bottom<=image.height) or right-left<8 or bottom-top<8:
        raise ValueError('Sélectionnez une zone plus grande à l’intérieur de l’écran.')
    crop=image.crop(rectangle)
    try:
        crop.thumbnail((2048,2048))
        output=io.BytesIO();crop.convert('RGB').save(output,'JPEG',quality=82)
        if output.tell()>2*1024*1024:raise ValueError('Choisissez une zone plus petite.')
        return 'data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode()
    finally:crop.close()


def capture():
    import os
    if os.name!='nt':raise ValueError('La sélection d’écran est disponible sur Windows.')
    import ctypes
    import clr
    clr.AddReference('System.Windows.Forms');clr.AddReference('System.Drawing')
    from System.Threading import Thread,ThreadStart,ApartmentState
    from System.Windows.Forms import Form,FormBorderStyle,FormStartPosition,Application,Timer,Keys,Cursors,AutoScaleMode,Label,DockStyle
    from System.Drawing import Color,Pen,Rectangle,Font
    from PIL import ImageGrab
    result={'cancelled':True}

    def select():
        image=None;form=None;timer=None;pen=None
        try:
            # Change only this helper thread's DPI context, preserving the client UI.
            try:ctypes.windll.user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
            except (AttributeError,OSError):pass
            left=ctypes.windll.user32.GetSystemMetrics(76);top=ctypes.windll.user32.GetSystemMetrics(77)
            width=ctypes.windll.user32.GetSystemMetrics(78);height=ctypes.windll.user32.GetSystemMetrics(79)
            image=ImageGrab.grab(all_screens=True)
            if image.size!=(width,height):raise ValueError('La disposition des écrans a changé. Réessayez.')
            form=Form();form.AutoScaleMode=getattr(AutoScaleMode,'None');form.StartPosition=FormStartPosition.Manual
            form.FormBorderStyle=getattr(FormBorderStyle,'None');form.Bounds=Rectangle(left,top,width,height)
            form.TopMost=True;form.ShowInTaskbar=False;form.BackColor=Color.Black;form.Opacity=.35;form.Cursor=Cursors.Cross;form.KeyPreview=True
            label=Label();label.Text='Sélectionnez une zone · Échap pour annuler';label.ForeColor=Color.White;label.BackColor=Color.Black;label.Dock=DockStyle.Top;label.Height=42;label.Font=Font('Segoe UI',12);form.Controls.Add(label)
            selection={'start':None,'end':None};pen=Pen(Color.LightSkyBlue,3)
            def down(sender,event):selection.update(start=(event.X,event.Y),end=None)
            def move(sender,event):
                if selection['start'] is not None:selection['end']=(event.X,event.Y);form.Invalidate()
            def paint(sender,event):
                if selection['start'] is None or selection['end'] is None:return
                a,b=selection['start'],selection['end'];event.Graphics.DrawRectangle(pen,min(a[0],b[0]),min(a[1],b[1]),abs(a[0]-b[0]),abs(a[1]-b[1]))
            def up(sender,event):
                if selection['start'] is None:return
                a,b=selection['start'],(event.X,event.Y)
                rectangle=(max(0,min(a[0],b[0])),max(0,min(a[1],b[1])),min(width,max(a[0],b[0])),min(height,max(a[1],b[1])))
                if rectangle[2]-rectangle[0]<8 or rectangle[3]-rectangle[1]<8:selection['start']=None;form.Invalidate();return
                result.update(cancelled=False,image=encode_region(image,rectangle));form.Close()
            def key(sender,event):
                if event.KeyCode==Keys.Escape:form.Close()
            form.MouseDown+=down;form.MouseMove+=move;form.MouseUp+=up;form.Paint+=paint;form.KeyDown+=key
            timer=Timer();timer.Interval=60000;timer.Tick+=lambda *_:form.Close();timer.Start()
            Application.Run(form)
        except Exception:
            result.clear();result['error']='La capture a échoué. Choisissez une image enregistrée ou réessayez.'
        finally:
            if timer is not None:timer.Stop();timer.Dispose()
            if form is not None:form.Dispose()
            if pen is not None:pen.Dispose()
            if image is not None:image.close()
    thread=Thread(ThreadStart(select));thread.SetApartmentState(ApartmentState.STA);thread.IsBackground=True;thread.Start();thread.Join(65000)
    if thread.IsAlive:raise ValueError('La sélection est encore ouverte. Fermez-la avec Échap.')
    if result.get('error'):raise ValueError(result['error'])
    return result
