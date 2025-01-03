from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, FileField, BooleanField
from wtforms.validators import DataRequired, DataRequired, Optional
import os
import string
import random
from flask_migrate import Migrate
from flask import send_from_directory
import os
from werkzeug.utils import secure_filename
import zipfile
import io
from flask import Response
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import shutil
from flask import jsonify
import csv
import pandas as pd



app = Flask(__name__)
app.config.from_object('config.Config')
db = SQLAlchemy(app)
app.secret_key = 'm565654dwdwewe2qwdfewfw63436'  # Cambia esto por algo más seguro en producción

# Configuraciones
app.secret_key = 'mi_clave_secreta'
app.config['SPOTIPY_CLIENT_ID'] = 'f9526f0f326f41e6a88b98bebdb2afe3'
app.config['SPOTIPY_CLIENT_SECRET'] = 'c67b4d612c944221ae4241b464117af9'
app.config['SPOTIPY_REDIRECT_URI'] = 'http://127.0.0.1:5000/callback'
app.config['SCOPE'] = 'playlist-modify-public playlist-modify-private user-library-read'

sp_oauth = SpotifyOAuth(
    client_id=app.config['SPOTIPY_CLIENT_ID'],
    client_secret=app.config['SPOTIPY_CLIENT_SECRET'],
    redirect_uri=app.config['SPOTIPY_REDIRECT_URI'],
    scope=app.config['SCOPE']
)

# Ruta para guardar las imágenes
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Login form
class LoginForm(FlaskForm):
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Ingresar')

    
class Fotografia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(100), nullable=False)
    archivo = db.Column(db.String(100), nullable=False)

# Función para crear un nombre de archivo seguro
def secure_filename_custom(filename):
    # Se asegura que el nombre del archivo sea seguro al eliminar caracteres no permitidos
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    return ''.join(c for c in filename if c in valid_chars)


class FotografiaForm(FlaskForm):
    nombre_usuario = StringField('Nombre de la Galería', validators=[DataRequired()])
    archivos = FileField('Subir Fotografías', render_kw={'multiple': True})
    submit = SubmitField('Subir Fotos')




@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        password = form.password.data

        if password == "administrador":
            session['role'] = 'admin'
            return redirect(url_for('administrador'))
        elif password == "invitado":
            session['role'] = 'invitado'
            return redirect(url_for('index'))
        else:
            flash("Contraseña incorrecta, inténtalo de nuevo.", 'danger')

    return render_template('login.html', form=form)


@app.route('/login', methods=['GET', 'POST'], endpoint='login_user')
def login():
    # Verifica si el usuario ya está autenticado a través de Spotify
    if 'token_info' in session:
        flash('Ya estás autenticado a través de Spotify.', 'success')
        return redirect(url_for('index'))  # O redirige a la página correspondiente

    if request.method == 'POST':
        # Si no hay autenticación de Spotify, puedes permitir login con contraseñas locales
        contraseña = request.form['contraseña']
        if contraseña == 'administrador':
            session['role'] = 'admin'
            flash('Inicio de sesión exitoso como administrador.', 'success')
            return redirect(url_for('administrador'))
        elif contraseña == 'guest':
            session['role'] = 'invitado'
            flash('Inicio de sesión exitoso como invitado.', 'success')
            return redirect(url_for('quien_eres'))
        elif contraseña == 'fotografo':
            session['role'] = 'fotografo'
            flash('Inicio de sesión exitoso como fotógrafo.', 'success')
            return redirect(url_for('uploading'))
        else:
            flash('Contraseña incorrecta.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/quien-eres', methods=['GET', 'POST'])
def quien_eres():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        if nombre:
            session['nombre_usuario'] = nombre
            flash(f'¡Hola, {nombre}!', 'success')
            return redirect(url_for('index'))  # Redirige al inicio o a donde prefieras
        else:
            flash('Por favor, introduce tu nombre.', 'danger')
    
    return render_template('quien_eres.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('login'))

# Carpeta donde se guardarán los videos
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads', 'videos')  
# Asegúrate de crear esta carpeta si no existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/index', methods=['GET', 'POST'])
def index():
    if 'role' not in session or session['role'] != 'invitado':
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Verifica si el archivo está presente
        if 'video' not in request.files:
            flash("No se seleccionó ningún archivo", "danger")
            return redirect(request.url)

        video = request.files['video']
        nombre = request.form.get('nombre')
        comentario = request.form.get('comentario')

        if video.filename == '':
            flash("No se seleccionó ningún archivo", "danger")
            return redirect(request.url)

        if video and allowed_file(video.filename):
            filename = secure_filename(video.filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Guardar el archivo en la carpeta 'videos'
            video.save(video_path)
            flash("¡Video subido con éxito! Gracias por tu mensaje.", "success")
            return redirect(url_for('index'))  # Redirige a la página principal
        else:
            flash("Tipo de archivo no permitido. Solo se aceptan archivos de video.", "danger")
            return redirect(request.url)

    return render_template('index.html')


def calcular_almacenamiento_usado(base_path=None):
    """
    Calcula el tamaño total de los archivos en todas las carpetas dentro de un directorio base.

    Args:
        base_path (str): Ruta del directorio base. Si no se especifica, se utiliza el directorio actual.
    
    Returns:
        int: Tamaño total en bytes de los archivos dentro del directorio base y sus subdirectorios.
    """
    if base_path is None:
        base_path = os.getcwd()  # Usar el directorio actual si no se especifica otro
    
    total_size = 0

    for dirpath, dirnames, filenames in os.walk(base_path):
        for filename in filenames:
            try:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
            except (OSError, FileNotFoundError) as e:
                # Manejar archivos que no puedan ser accedidos o que hayan sido eliminados
                print(f"Error al acceder a {filepath}: {e}")
    
    return total_size


@app.route('/administrador')
def administrador():
    if 'role' not in session or session['role'] != 'admin':
        flash('Acceso denegado. Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('login'))

    # Calcular el almacenamiento utilizado
    almacenamiento_usado = calcular_almacenamiento_usado()
    almacenamiento_maximo = 10 * 1024**3  # 10 GB en bytes
    porcentaje_usado = (almacenamiento_usado / almacenamiento_maximo) * 100

    try:
        invitados = Invitado.query.all()  # Obtener todos los invitados
        print(invitados)  # Verificar si los datos se están obteniendo correctamente
    except Exception as e:
        flash(f"Error al acceder a la base de datos: {e}", "danger")
        invitados = []

    return render_template('administrador.html', invitados=invitados, porcentaje_usado=porcentaje_usado)


@app.route('/eliminar_acompanante/<int:id>', methods=['POST'])
def eliminar_acompanante(id):
    invitado = Invitado.query.get_or_404(id)
    if invitado.acompanante:
        invitado.acompanante = False
        invitado.nombre_acompanante = None  # Limpia el nombre del acompañante
        db.session.commit()
        flash('El acompañante ha sido eliminado.', 'success')
    else:
        flash('Este invitado no tiene acompañante para eliminar.', 'warning')
    return redirect(url_for('administrador'))



@app.route('/exportar_invitados', methods=['GET'])
def exportar_invitados():
    try:
        invitados = Invitado.query.all()
        
        # Crear una respuesta CSV
        si = io.StringIO()
        escritor = csv.writer(si)
        
        # Escribir encabezados
        escritor.writerow([
            'Nombre', 'Apellido', 'Teléfono', 'Acompañante', 
            'Nombre del Acompañante', 'Intolerancia Alimentaria', 
            'Comentarios', 'Canción Favorita'
        ])
        
        # Escribir datos de los invitados
        for invitado in invitados:
            escritor.writerow([
                invitado.nombre, 
                invitado.apellido, 
                invitado.telefono, 
                'Sí' if invitado.acompanante else 'No',
                invitado.nombre_acompanante or 'N/A',
                invitado.intolerancia or 'Ninguna',
                invitado.comentarios or 'Sin comentarios',
                invitado.cancion or 'No especificada'
            ])
        
        # Crear respuesta
        respuesta = Response(si.getvalue(), mimetype='text/csv')
        respuesta.headers['Content-Disposition'] = 'attachment; filename=invitados.csv'
        return respuesta

    except Exception as e:
        flash(f"Error al exportar la lista de invitados: {e}", "danger")
        return redirect(url_for('administrador'))

@app.route('/exportar_invitados_excel', methods=['GET'])
def exportar_invitados_excel():
    try:
        invitados = Invitado.query.all()
        
        # Crear un DataFrame
        data = [
            {
                'Nombre': invitado.nombre,
                'Apellido': invitado.apellido,
                'Teléfono': invitado.telefono,
                'Acompañante': 'Sí' if invitado.acompanante else 'No',
                'Nombre del Acompañante': invitado.nombre_acompanante or 'N/A',
                'Intolerancia Alimentaria': invitado.intolerancia or 'Ninguna',
                'Comentarios': invitado.comentarios or 'Sin comentarios',
                'Canción Favorita': invitado.cancion or 'No especificada',
            }
            for invitado in invitados
        ]
        df = pd.DataFrame(data)
        
        # Crear el archivo Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Invitados')
        
        # Enviar el archivo al cliente
        output.seek(0)
        return send_file(
            output, 
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='invitados.xlsx'
        )

    except Exception as e:
        flash(f"Error al exportar la lista de invitados: {e}", "danger")
        return redirect(url_for('administrador'))
    
@app.route('/eliminar_invitado/<int:id>', methods=['POST'])
def eliminar_invitado(id):
    invitado = Invitado.query.get_or_404(id)  # Buscar invitado por ID
    db.session.delete(invitado)  # Eliminar el invitado
    db.session.commit()  # Confirmar los cambios en la base de datos
    flash('Invitado eliminado correctamente.', 'success')  # Mensaje de confirmación
    return redirect(url_for('administrador'))  # Redirigir a la página de administrador

class Invitado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(15), nullable=True)
    acompanante = db.Column(db.Boolean, default=False)
    nombre_acompanante = db.Column(db.String(100), nullable=True)
    es_nino = db.Column(db.Boolean, default=False)
    es_nino_acompanante = db.Column(db.Boolean, default=False)
    intolerancia = db.Column(db.String(200), nullable=True)
    comentarios = db.Column(db.String(500), nullable=True)
    cancion = db.Column(db.String(200), nullable=True)


class InvitadoForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    apellido = StringField('Apellido', validators=[DataRequired()])
    telefono = StringField('Teléfono', validators=[DataRequired()])
    es_nino = BooleanField('Es niño', validators=[Optional()])
    acompanante = BooleanField('Tiene acompañante', validators=[Optional()])
    nombre_acompanante = StringField('Nombre del acompañante', validators=[Optional()])
    es_nino_acompanante = BooleanField('El acompañante es niño', validators=[Optional()])
    intolerancia = StringField('Intolerancia', validators=[Optional()])
    comentarios = StringField('Comentarios', validators=[Optional()])
    cancion = StringField('Canción', validators=[Optional()])
    submit = SubmitField('Enviar')


@app.route('/invitado', methods=['GET', 'POST'])
def invitado():
    if 'role' not in session or session['role'] != 'invitado':
        flash('Acceso denegado. Debes iniciar sesión como invitado.', 'danger')
        return redirect(url_for('login'))

    form = InvitadoForm()
    if form.validate_on_submit():
        nuevo_invitado = Invitado(
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            telefono=form.telefono.data,
            es_nino=form.es_nino.data,
            acompanante=form.acompanante.data,
            nombre_acompanante=form.nombre_acompanante.data if form.acompanante.data else None,
            es_nino_acompanante=form.es_nino_acompanante.data if form.acompanante.data else None,
            intolerancia=form.intolerancia.data,
            comentarios=form.comentarios.data,
            cancion=form.cancion.data
        )
        db.session.add(nuevo_invitado)
        db.session.commit()
        flash('Respuesta registrada', 'success')
        return redirect(url_for('index'))
    return render_template('invitado.html', form=form)



# Configura los tipos de archivo permitidos
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'}

# Esta función verifica si el archivo tiene una extensión permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/fotografias', methods=['GET', 'POST'])
def fotografias():
    form = FotografiaForm()

    if form.validate_on_submit():
        if 'archivos' in request.files:
            archivos = request.files.getlist('archivos')
            nombre_usuario = form.nombre_usuario.data
            directorio_usuario = os.path.join(app.config['UPLOAD_FOLDER'], nombre_usuario)

            # Crear el directorio si no existe
            if not os.path.exists(directorio_usuario):
                os.makedirs(directorio_usuario)

            # Iterar sobre todos los archivos seleccionados
            for archivo in archivos:
                if archivo and archivo.filename:
                    # Validar la extensión del archivo
                    if not allowed_file(archivo.filename):
                        flash(f'El archivo {archivo.filename} no es válido. Solo se permiten archivos de video e imagen.', 'danger')
                        return redirect(url_for('fotografias'))

                    try:
                        filename = secure_filename(archivo.filename)
                        filepath = os.path.join(directorio_usuario, filename)
                        archivo.save(filepath)

                        # Guardar información en la base de datos
                        nueva_foto = Fotografia(nombre_usuario=nombre_usuario, archivo=filename)
                        db.session.add(nueva_foto)
                    except Exception as e:
                        flash(f'Error al subir el archivo {archivo.filename}: {str(e)}', 'danger')
                        return redirect(url_for('fotografias'))

            # Confirmar la subida de todos los archivos
            db.session.commit()
            flash('Fotografías subidas con éxito', 'success')
            return redirect(url_for('fotografias'))
        else:
            flash('No se seleccionaron archivos', 'danger')

    return render_template('fotografias.html', form=form)


    return render_template('fotografias.html', form=form)

# Nueva ruta para la subida de archivos con barra de progreso
@app.route('/subir_archivos', methods=['POST'])
def subir_archivos():
    archivos = request.files.getlist('archivos')
    nombre_usuario = request.form.get('nombre_usuario')
    directorio_usuario = os.path.join(app.config['UPLOAD_FOLDER'], nombre_usuario)

    if not os.path.exists(directorio_usuario):
        os.makedirs(directorio_usuario)

    for archivo in archivos:
        if archivo and archivo.filename:
            filename = secure_filename(archivo.filename)
            filepath = os.path.join(directorio_usuario, filename)
            archivo.save(filepath)

            # Guardar en la base de datos (opcional)
            nueva_foto = Fotografia(nombre_usuario=nombre_usuario, archivo=filename)
            db.session.add(nueva_foto)
    db.session.commit()

    return 'Subida completada', 200




@app.route('/galerias')
def galerias():
    # Obtener todos los directorios dentro de 'uploads', excluyendo la carpeta 'fotografo'
    directorios = [
        d for d in os.listdir(app.config['UPLOAD_FOLDER'])
        if os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], d)) and d != 'fotografo'
    ]

    # Crear una lista de diccionarios con el usuario y su primera foto
    galerias = []
    for directorio in directorios:
        ruta_directorio = os.path.join(app.config['UPLOAD_FOLDER'], directorio)
        fotos = sorted(os.listdir(ruta_directorio))  # Aseguramos un orden consistente
        primera_foto = fotos[0] if fotos else None  # Seleccionamos la primera foto si hay
        galerias.append({
            'usuario': directorio,
            'primera_foto': primera_foto
        })

    return render_template('galerias.html', galerias=galerias)



# Ruta para ver la galería de un usuario
@app.route('/galeria/<nombre_usuario>')
def ver_galeria(nombre_usuario):
    fotos_usuario = Fotografia.query.filter_by(nombre_usuario=nombre_usuario).all()
    return render_template('ver_galeria.html', fotos=fotos_usuario, nombre_usuario=nombre_usuario)


@app.route('/uploads/<path:filename>')
def upload_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/descargar_todas/<nombre_usuario>')
def descargar_todas(nombre_usuario):
    # Crear un archivo ZIP en memoria
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Buscar todas las fotos del usuario
        fotos_usuario = Fotografia.query.filter_by(nombre_usuario=nombre_usuario).all()
        for foto in fotos_usuario:
            # Ruta de cada archivo original
            archivo_path = os.path.join(app.config['UPLOAD_FOLDER'], nombre_usuario, foto.archivo)
            zip_file.write(archivo_path, foto.archivo)
    
    zip_buffer.seek(0)  # Volver al principio del archivo ZIP
    return Response(
        zip_buffer,
        mimetype='application/zip',
        headers={"Content-Disposition": f"attachment; filename={nombre_usuario}_galeria.zip"}
    )





@app.route('/download_file/<path:filename>')
def download_file(filename):
    # Usamos la misma función send_from_directory que en upload_file
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/download_all_files/<nombre_galeria>')
def download_all_files(nombre_galeria):
    ruta_directorio = os.path.join(app.config['UPLOAD_FOLDER'], "fotografo", nombre_galeria)

    # Verificar que la carpeta de la galería existe
    if not os.path.exists(ruta_directorio):
        flash("La galería solicitada no existe.", "danger")
        return redirect(url_for('ver_galeria_fotografo', nombre_galeria=nombre_galeria))
    
    # Crear un archivo ZIP en memoria
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Listar las fotos en la galería
        fotos = sorted(os.listdir(ruta_directorio))
        for foto in fotos:
            # Asegurarse de que solo agregamos archivos válidos
            if foto.lower().endswith(('jpg', 'jpeg', 'png', 'gif')):
                archivo_path = os.path.join(ruta_directorio, foto)
                zip_file.write(archivo_path, foto)  # Escribir el archivo en el ZIP
    
    # Volver al principio del buffer antes de devolverlo
    zip_buffer.seek(0)

    # Devolver el archivo ZIP como respuesta
    return send_file(zip_buffer,
                     mimetype='application/zip',
                     as_attachment=True,
                     download_name=f"{nombre_galeria}_fotos.zip")

@app.route('/diaboda')
def diaboda():
    return render_template('diaboda.html')


# Ruta para la página de la playlist colaborativa
@app.route('/playlist')
def playlist_colaborativa():
    return render_template('playlist.html')

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'cabina')

upload_folder = os.path.join('static', 'invitados')

# Verificar si la carpeta no existe y crearla
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

app.config['UPLOAD_FOLDER'] = upload_folder



cabinafolder= os.path.join('static', 'cabina')

# Verificar si la carpeta no existe y crearla
if not os.path.exists(cabinafolder):
    os.makedirs(cabinafolder)

app.config['cabinafolder'] = cabinafolder

# Ruta para procesar el formulario
@app.route('/cabina_confesiones', methods=['POST'])
def cabina_confesiones():
    if 'video' not in request.files:
        flash('No se seleccionó ningún archivo.', 'danger')
        return redirect(url_for('diaboda'))

    video = request.files['video']
    nombre = request.form.get('nombre')
    comentario = request.form.get('comentario')

    if video and allowed_file(video.filename):
        filename = secure_filename(video.filename)
        video_path = os.path.join(app.config['cabinafolder'], filename)
        video.save(video_path)

        # Aquí puedes guardar `nombre`, `comentario` y `video_path` en tu base de datos si tienes una.
        flash('¡Gracias por tu confesión! El video ha sido subido con éxito.', 'success')
    else:
        flash('Formato de archivo no permitido. Por favor, sube un video válido.', 'danger')

    return redirect(url_for('diaboda'))


def allowed_file_cabina(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png', 'gif'}

app.config['MURO_FOLDER'] = os.path.join(app.root_path, 'static', 'muro_folder')
# Modelo de Publicación
class Publicacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    texto = db.Column(db.String(220), nullable=False)
    foto = db.Column(db.String(120), nullable=True)
    usuario = db.Column(db.String(100), nullable=False)
    votos = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Publicacion {self.texto}>"

# Modelo de Voto
class Voto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('publicacion.id'), nullable=False)

# Ruta principal del muro
@app.route('/muro', methods=['GET', 'POST'])
def muro():
    if 'nombre_usuario' not in session:
        return redirect(url_for('quien_eres'))

    if request.method == 'POST':
        texto = request.form['texto']
        foto = request.files.get('foto')
        usuario = session['nombre_usuario']

        # Guardar la foto si es válida
        foto_filename = None
        if foto and allowed_file_cabina(foto.filename):
            foto_filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['MURO_FOLDER'], foto_filename))

        # Crear y guardar la publicación
        nueva_publicacion = Publicacion(
            texto=texto,
            foto=foto_filename,
            usuario=usuario
        )
        db.session.add(nueva_publicacion)
        db.session.commit()

    # Ordenar publicaciones
    sort_by = request.args.get('sort', 'votos')
    if sort_by == 'recientes':
        posts = Publicacion.query.order_by(Publicacion.id.desc()).all()
    else:
        posts = Publicacion.query.order_by(Publicacion.votos.desc()).all()

    return render_template('muro.html', posts=posts, sort_by=sort_by)

# Servir imágenes desde la carpeta estática
@app.route('/static/muro_folder/<path:filename>')
def serve_muro_files(filename):
    return send_from_directory(app.config['MURO_FOLDER'], filename)

# Ruta para votar
@app.route('/votar/<int:post_id>', methods=['POST'])
def votar(post_id):
    if 'nombre_usuario' not in session:
        flash('Debes iniciar sesión para votar.', 'warning')
        return redirect(url_for('login'))

    usuario = session['nombre_usuario']
    post = Publicacion.query.get(post_id)

    if not post:
        flash('La publicación no existe.', 'danger')
        return redirect(url_for('muro'))

    # Verificar si ya votó
    voto_existente = Voto.query.filter_by(usuario=usuario, post_id=post_id).first()
    if voto_existente:
        flash('Ya has votado esta publicación.', 'info')
        return redirect(url_for('muro'))

    # Registrar el voto
    nuevo_voto = Voto(usuario=usuario, post_id=post_id)
    db.session.add(nuevo_voto)
    post.votos += 1
    db.session.commit()

    flash('¡Voto registrado!', 'success')
    return redirect(url_for('muro'))

# Crear las tablas
with app.app_context():
    db.create_all()


@app.route('/send_to_muro', methods=['POST'])
def send_to_muro():
    data = request.get_json()
    foto = data.get('foto')
    usuario = data.get('usuario')
    comentario = data.get('comentario', 'Foto publicada')

    if not foto or not usuario:
        return jsonify(success=False, message="Datos incompletos"), 400

    # Ruta del archivo
    ruta_archivo = os.path.join(app.config['UPLOAD_FOLDER'], usuario, foto)
    if not os.path.exists(ruta_archivo):
        return jsonify(success=False, message="Archivo no encontrado"), 404

    # Copiar al muro
    muro_ruta = os.path.join(app.config['MURO_FOLDER'], foto)
    shutil.copy(ruta_archivo, muro_ruta)

    # Crear publicación con comentario
    nueva_publicacion = Publicacion(
        texto=comentario,
        foto=foto,
        usuario=usuario
    )
    db.session.add(nueva_publicacion)
    db.session.commit()

    return jsonify(success=True, message="Publicación creada correctamente")




from flask import session, redirect, url_for, flash

@app.route('/muroadmin', methods=['GET'])
def muroadmin():
    # Verificar si el usuario está autenticado y tiene rol de administrador
    if 'nombre_usuario' not in session or session.get('role') != 'admin':
        flash('Acceso denegado. Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('quien_eres'))

    # Obtener publicaciones ordenadas por ID descendente
    posts = Publicacion.query.order_by(Publicacion.id.desc()).all()
    return render_template('muroadmin.html', posts=posts)


@app.route('/eliminar/<int:post_id>', methods=['POST'])
def eliminar_post(post_id):
    if 'nombre_usuario' not in session:
        flash('Debes iniciar sesión para gestionar el muro.', 'warning')
        return redirect(url_for('login'))

    post = Publicacion.query.get(post_id)

    if not post:
        flash('La publicación no existe.', 'danger')
        return redirect(url_for('muroadmin'))

    # Eliminar la foto si existe
    if post.foto:
        foto_path = os.path.join(app.config['MURO_FOLDER'], post.foto)
        if os.path.exists(foto_path):
            os.remove(foto_path)

    # Eliminar los votos asociados y la publicación
    Voto.query.filter_by(post_id=post_id).delete()
    db.session.delete(post)
    db.session.commit()

    flash('Publicación eliminada correctamente.', 'success')
    return redirect(url_for('muroadmin'))




app.config['PHOTO_FOLDER'] = 'static/fotografo'
# Crear carpeta de fotos si no existe
os.makedirs(app.config['PHOTO_FOLDER'], exist_ok=True)

# Subir fotografías
@app.route('/uploading', methods=['GET', 'POST'])
def uploading():
    if request.method == 'POST':
        momento = request.form.get('momento')
        archivos = request.files.getlist('archivos')

        if not momento or not archivos:
            flash('Debes completar todos los campos.', 'danger')
            return redirect(url_for('uploading'))

        momento_folder = os.path.join(app.config['PHOTO_FOLDER'], secure_filename(momento))
        os.makedirs(momento_folder, exist_ok=True)

        for archivo in archivos:
            if archivo:
                archivo.save(os.path.join(momento_folder, secure_filename(archivo.filename)))

        flash(f'Fotos subidas al momento: {momento}', 'success')
        return redirect(url_for('uploading'))

    return render_template('uploading.html')

@app.route('/galeriasfotografo')
def galerias_fotografo():
    # Ruta a la carpeta 'fotografo' dentro de 'static'
    photographer_dir = os.path.join(app.static_folder, 'fotografo')
    
    # Lista de subcarpetas
    subfolders = []
    
    # Recorremos las subcarpetas
    for folder in os.listdir(photographer_dir):
        folder_path = os.path.join(photographer_dir, folder)
        
        # Verificamos si es una carpeta
        if os.path.isdir(folder_path):
            # Lista las fotos dentro de la subcarpeta
            photos = [f for f in os.listdir(folder_path) if f.lower().endswith(('jpg', 'jpeg', 'png'))]
            if photos:
                # Tomamos la primera foto como miniatura
                thumbnail = photos[0]
                subfolders.append({
                    'folder': folder,
                    'thumbnail': os.path.join('fotografo', folder, thumbnail)  # Ruta correcta a la imagen
                })
    
    return render_template('galeriasfotografo.html', subfolders=subfolders)

@app.route('/media/<path:filename>')
def serve_image(filename):
    return send_from_directory(app.config['PHOTO_FOLDER'], filename)


@app.route('/fotografo/galeria/<momento>')
def fotografogaleriamomento(momento):
    # Ruta base para las fotos
    base_path = os.path.join(app.static_folder, 'fotografo')

    # Construir la ruta para la subcarpeta correspondiente al 'momento'
    subcarpeta_path = os.path.join(base_path, momento)

    # Comprobar si la subcarpeta existe
    if not os.path.isdir(subcarpeta_path):
        return f"No se encontró la galería para el momento: {momento}", 404

    # Obtener las fotos en la subcarpeta
    fotos = [
        foto for foto in os.listdir(subcarpeta_path)
        if foto.lower().endswith(('png', 'jpg', 'jpeg', 'gif'))
    ]

    # Si no hay fotos, mostrar un mensaje adecuado
    if not fotos:
        return f"No hay fotos disponibles para el momento: {momento}", 404

    # Recuperar el nombre del usuario (puedes adaptarlo según tu lógica)
    nombre_usuario = session.get('usuario_actual', 'anonimo')

    # Pasar las fotos, el momento y el nombre de usuario al template
    return render_template(
        'fotografogaleriamomento.html',
        momento=momento,
        fotos=fotos,
        nombre_usuario=nombre_usuario
    )




# Descargar todas las fotos (en un futuro, puedes implementar esto como un ZIP)
@app.route('/fotografo/descargar_todas/<momento>')
def descargar_todasfotografo(momento):
    flash('Funcionalidad para descargar todas las fotos aún no implementada.', 'info')
    return redirect(url_for('galeriafotografo', momento=momento))

@app.route('/fotografo/galeria/deliver_to_muro', methods=['POST'])
def deliver_to_muro():
    data = request.get_json()

    # Obtener los datos
    foto = data.get('foto')
    momento = data.get('momento')
    comentario = data.get('comentario')
    usuario = session.get('nombre_usuario', 'anónimo')


    # Verificar si hay datos completos
    if not foto:
        return jsonify(success=False, message="Falta la imagen"), 400

    if not momento:
        return jsonify(success=False, message="Falta el momento"), 400

    if not comentario or not comentario.strip():
        return jsonify(success=False, message="Falta el comentario"), 400

    if not usuario:
        return jsonify(success=False, message="Falta el usuario"), 400

    # Ruta de la foto
    foto_path = os.path.join(app.config['PHOTO_FOLDER'], momento, foto)

    # Verificar si la foto existe
    if not os.path.exists(foto_path):
        return jsonify(success=False, message="La foto no fue encontrada en el servidor"), 404

    # Mover la foto al muro o realizar alguna acción
    muro_path = os.path.join(app.config['MURO_FOLDER'], foto)
    shutil.copy(foto_path, muro_path)

    # Crear una nueva publicación en la base de datos
    nueva_publicacion = Publicacion(
        texto=comentario,
        foto=foto,
        usuario=usuario
    )
    db.session.add(nueva_publicacion)
    db.session.commit()

    return jsonify(success=True, message="Publicación creada correctamente")







@app.route('/schedule')
def schedule():
    return render_template('schedule.html')


@app.route('/gifts')
def gifts():
    return render_template('/gifts.html')

@app.route('/location')
def location():
    return render_template('/location.html')

@app.route('/dresscode')
def dresscode():
    return render_template('/dresscode.html')

@app.route('/menu')
def menu():
    return render_template('/menu.html')


@app.route('/faq')
def faq():
    return render_template('/faq.html')

#MAQUETACIONES EXTRAS SE DEBERA BORRAR
@app.route('/login2')
def login2():
    return render_template('login_2.html')

#MAQUETACIONES EXTRAS SE DEBERA BORRAR
@app.route('/login3')
def login3():
    return render_template('login_3.html')

#MAQUETACIONES EXTRAS SE DEBERA BORRAR
@app.route('/login4')
def login4():
    return render_template('login_4.html')

#MAQUETACIONES EXTRAS SE DEBERA BORRAR
@app.route('/login5')
def login5():
    return render_template('login_5.html')

#MAQUETACIONES EXTRAS SE DEBERA BORRAR
@app.route('/login6')
def login6():
    return render_template('login_6.html')

#MAQUETACIONES EXTRAS SE DEBERA BORRAR
@app.route('/login7')
def login7():
    return render_template('login_7.html')

#MAQUETACIONES EXTRAS SE DEBERA BORRAR
@app.route('/login8')
def login8():
    return render_template('login_8.html')

#MAQUETACIONES EXTRAS SE DEBERA BORRAR
@app.route('/login9')
def login9():
    return render_template('login_9.html')

#MAQUETACIONES EXTRAS SE DEBERA BORRAR
@app.route('/login10')
def login10():
    return render_template('login_10.html')


#MAQUETACIONES EXTRAS SE DEBERA BORRAR
@app.route('/login11')
def login11():
    return render_template('login_11.html')

#MAQUETACIONES EXTRAS SE DEBERA BORRAR
@app.route("/login12")
def login12():
    return render_template('login_12.html')


if __name__ == '__main__':
    app.run(debug=True)

