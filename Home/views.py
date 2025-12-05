from django.shortcuts import render, redirect
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime

def index(request):
    context = {
        'db_connected': False,
        'error_message': None,
        'db_info': {},
        'tables': [],
        'table_data': {},
        'login_error': None,
        'login_success': None
    }
    
    if request.method == 'POST' and request.POST.get('action') == 'login':
        email = request.POST['email']
        password = request.POST['password']
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, nombre_completo, password FROM usuarios WHERE email = %s", [email])
                usuario = cursor.fetchone()
                
                if usuario and check_password(password, usuario[2]):
                    # Login exitoso - guardar en sesión
                    request.session['usuario_id'] = usuario[0]
                    request.session['usuario_nombre'] = usuario[1]
                    return redirect('panel')
                else:
                    context['login_error'] = '❌ Correo o contraseña incorrectos. ¿No tienes cuenta? Regístrate.'
        except Exception as e:
            context['login_error'] = f'Error: {e}'
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version(), current_database(), current_user;")
            db_info = cursor.fetchone()
            context['db_info'] = {
                'version': db_info[0],
                'name': db_info[1],
                'user': db_info[2]
            }
            
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
            context['tables'] = [row[0] for row in cursor.fetchall()]
            context['db_connected'] = True
            
    except Exception as e:
        context['error_message'] = str(e)
    
    return render(request, 'index.html', context)

def panel(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('index')
    
    usuario_nombre = request.session.get('usuario_nombre', 'Usuario')
    
    # Función para obtener medicamentos
    def obtener_medicamentos():
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM medicamentos WHERE usuario_id = %s ORDER BY creado_en DESC", [usuario_id])
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # Obtener medicamentos inicialmente
    medicamentos = obtener_medicamentos()
    
    if request.method == 'POST':
        try:
            # CORRECCIÓN: Manejar correctamente los campos opcionales
            hora_personalizada = request.POST.get('hora_personalizada')
            if hora_personalizada == '':
                hora_personalizada = None  # Convertir cadena vacía a None para PostgreSQL
                
            fecha_fin = request.POST.get('fecha_fin')
            if fecha_fin == '':
                fecha_fin = None  # Convertir cadena vacía a None para PostgreSQL
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO medicamentos 
                    (nombre_medicamento, dosis, frecuencia, horario, hora_personalizada, 
                     fecha_inicio, fecha_fin, instrucciones, usuario_id, creado_en)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, [
                    request.POST['nombre_medicamento'],
                    request.POST['dosis'],
                    request.POST['frecuencia'],
                    request.POST['horario'],
                    hora_personalizada,  # Usar None en lugar de cadena vacía
                    request.POST['fecha_inicio'],
                    fecha_fin,  # Usar None en lugar de cadena vacía
                    request.POST['instrucciones'],
                    usuario_id
                ])
            
            # Obtener lista actualizada de medicamentos después del INSERT
            medicamentos = obtener_medicamentos()
            
            return render(request, 'panel.html', {
                'success': 'Medicamento registrado correctamente',
                'usuario_nombre': usuario_nombre,
                'medicamentos': medicamentos
            })
            
        except Exception as e:
            # En caso de error, mantener la lista actual de medicamentos
            return render(request, 'panel.html', {
                'error': f'Error: {str(e)}',
                'usuario_nombre': usuario_nombre,
                'medicamentos': medicamentos
            })
    
    # GET request - ya tenemos los medicamentos
    return render(request, 'panel.html', {
        'medicamentos': medicamentos,
        'usuario_nombre': usuario_nombre
    })

def registro(request):
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO usuarios 
                    (nombre_completo, email, celular, departamento, ciudad_localidad, direccion, password, is_active, is_staff, is_superuser, fecha_registro)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, [
                    request.POST['nombre_completo'],
                    request.POST['email'],
                    request.POST['celular'],
                    request.POST['departamento'],
                    request.POST['ciudad_localidad'],
                    request.POST['direccion'],
                    make_password(request.POST['password']),
                    True, 
                    False, 
                    False  
                ])
            return redirect('index')
        except Exception as e:
            return HttpResponse(f"Error: {e}")
    
    return render(request, 'registro.html')

def logout_view(request):
    request.session.flush()
    return redirect('index')

# ============================================================
# NUEVAS APIS PARA LA APP ANDROID
# ============================================================

@csrf_exempt
def api_medicamentos(request):
    """API simplificada para debug"""
    try:
        usuario_id = request.GET.get('usuario_id')
        
        if not usuario_id:
            return JsonResponse({'error': 'usuario_id requerido'}, status=400)
        
        # Respuesta simple de prueba
        return JsonResponse({
            'success': True,
            'medicamentos': [
                {
                    'id': 1,
                    'nombre_medicamento': 'Medicamento de prueba',
                    'dosis': '1 tableta',
                    'frecuencia': 'diario',
                    'horario': 'manana',
                    'hora_personalizada': None,
                    'instrucciones': 'Instrucciones de prueba'
                }
            ],
            'total': 1,
            'debug': f'usuario_id recibido: {usuario_id}'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Error en servidor: {str(e)}'}, status=500)
@csrf_exempt
def api_login(request):
    """API para que la app Android pueda autenticarse"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return JsonResponse({'error': 'Email y contraseña requeridos'}, status=400)
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, nombre_completo, password 
                    FROM usuarios 
                    WHERE email = %s
                """, [email])
                
                usuario = cursor.fetchone()
                
                if usuario and check_password(password, usuario[2]):
                    # Login exitoso - crear sesión
                    request.session['usuario_id'] = usuario[0]
                    request.session['usuario_nombre'] = usuario[1]
                    
                    return JsonResponse({
                        'success': True,
                        'usuario_id': usuario[0],
                        'usuario_nombre': usuario[1],
                        'message': 'Login exitoso'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Credenciales incorrectas'
                    }, status=401)
                    
        except Exception as e:
            return JsonResponse({'error': f'Error en el servidor: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@csrf_exempt
def api_logout(request):
    """API para que la app Android pueda cerrar sesión"""
    request.session.flush()
    return JsonResponse({'success': True, 'message': 'Sesión cerrada'})

@csrf_exempt
def api_mi_id(request):
    """API temporal para ver el usuario_id de la sesión"""
    usuario_id = request.session.get('usuario_id')
    return JsonResponse({
        'usuario_id': usuario_id,
        'usuario_nombre': request.session.get('usuario_nombre'),
        'esta_logueado': usuario_id is not None
    })