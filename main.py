from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from http import HTTPStatus
import re
import json
import os


class BlogHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.recipes_file = 'recipes.json'
        super().__init__(*args, **kwargs)

    def get_recipes(self):
        try:
            if os.path.exists(self.recipes_file):
                with open(self.recipes_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            print(f"Ошибка при загрузке рецептов: {e}")
            return {}

    def save_recipes(self, recipes):
        try:
            with open(self.recipes_file, 'w', encoding='utf-8') as f:
                json.dump(recipes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении рецептов: {e}")

    def do_GET(self):
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)

        routes = [
            (r'^/$', self.home),
            (r'^/recipe/([\w-]+)$', self.recipe),
            (r'^/about$', self.about),
            (r'^/create$', self.create_recipe),
            (r'^/style\.css$', self.css),
        ]

        for pattern, handler in routes:
            match = re.match(pattern, path)
            if match:
                return handler(*match.groups(), query=query)

        self.error_404()

    def do_POST(self):
        path = urlparse(self.path).path

        if path == '/create':
            self.handle_create_recipe()
        else:
            self.error_404()

    def handle_create_recipe(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        form_data = parse_qs(post_data)

        title = form_data.get('title', [''])[0].strip()
        recipe_id = form_data.get('recipe_id', [''])[0].strip().lower()
        ingredients_text = form_data.get('ingredients', [''])[0]
        instructions = form_data.get('instructions', [''])[0].strip()

        if not title or not recipe_id or not ingredients_text or not instructions:
            self.send_error_response('Все поля обязательны для заполнения!')
            return

        if not re.match(r'^[a-z0-9-]+$', recipe_id):
            self.send_error_response('ID рецепта может содержать только английские буквы, цифры и дефисы!')
            return

        ingredients = [ing.strip() for ing in ingredients_text.split('\n') if ing.strip()]

        if not ingredients:
            self.send_error_response('Добавьте хотя бы один ингредиент!')
            return

        recipes = self.get_recipes()

        if recipe_id in recipes:
            self.send_error_response('Рецепт с таким ID уже существует!')
            return

        recipes[recipe_id] = {
            'title': title,
            'ingredients': ingredients,
            'instructions': instructions
        }

        self.save_recipes(recipes)

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Location', f'/recipe/{recipe_id}')
        self.end_headers()

    def send_error_response(self, message):
        try:
            with open('error.html', 'r', encoding='utf-8') as f:
                html_content = f.read()

            html_content = html_content.replace('%%error_message%%', message)

            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        except:
            self.error_404()

    def home(self, query=None):
        recipes = self.get_recipes()

        recipes_html = ''
        for recipe_id, recipe in recipes.items():
            recipes_html += f'''
                <div class="recipe-card">
                    <h3>{recipe['title']}</h3>
                    <p>{recipe['instructions'][:100]}{'...' if len(recipe['instructions']) > 100 else ''}</p>
                    <a href="/recipe/{recipe_id}" class="btn">Смотреть рецепт</a>
                </div>
            '''

        if not recipes:
            recipes_html = '<p>Пока нет рецептов. <a href="/create">Создайте первый!</a></p>'

        self.send_html('index.html', {'recipes': recipes_html})

    def recipe(self, recipe_id, query=None):
        recipes = self.get_recipes()
        recipe = recipes.get(recipe_id)

        if recipe:
            ingredients_list = ''.join(f'<li>{ing}</li>'
                                       for ing in recipe['ingredients'])

            self.send_html('recipe.html', {
                'title': recipe['title'],
                'ingredients': ingredients_list,
                'instructions': recipe['instructions']
            })
        else:
            self.error_404()

    def create_recipe(self, query=None):
        self.send_html('create_recipe.html')

    def about(self, query=None):
        self.send_html('about.html')

    def css(self, query=None):
        try:
            with open('style.css', 'r', encoding='utf-8') as f:
                css = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-type', 'text/css; charset=utf-8')
            self.end_headers()
            self.wfile.write(css.encode('utf-8'))
        except:
            self.error_404()

    def send_html(self, filename, context=None):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                html_content = f.read()

            if context:
                for key, value in context.items():
                    html_content = html_content.replace(f'%%{key}%%', value)

            self.send_response(HTTPStatus.OK)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        except:
            self.error_404()

    def error_404(self):
        try:
            with open('404.html', 'r', encoding='utf-8') as f:
                html_content = f.read()

            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        except:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            error_html = "<h1>404</h1><p>Страница не найдена</p><a href='/'>На главную</a>"
            self.wfile.write(error_html.encode('utf-8'))


def run_server():
    server = HTTPServer(('localhost', 8000), BlogHandler)
    print('Сервер запущен: http://localhost:8000')
    server.serve_forever()


if __name__ == '__main__':
    run_server()