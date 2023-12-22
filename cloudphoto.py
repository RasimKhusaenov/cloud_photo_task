import argparse
import configparser
from configparser import NoOptionError
import boto3
import sys
import os
from airium import Airium

CONFIG_PATH = "./.config/cloudphotorc"

def initialize():
  config = configparser.ConfigParser()
  config.read(CONFIG_PATH)

  user_session = boto3.session.Session(aws_access_key_id=config['default']['aws_access_key_id'],
                                       aws_secret_access_key=config['default']['aws_secret_access_key'],
                                       region_name='ru-central1')
  user_resource = user_session.resource(service_name='s3', endpoint_url=config['default']['endpoint_url'])

  return user_resource, config


def uploadPhotos(path, directory, my_bucket):
  included_extensions = [".jpg", ".jpeg"]
  files = [fn for fn in os.listdir(path + "/")
              if any(fn.endswith(ext) for ext in included_extensions)]

  for file in files:
    try:
      path_to_file = path + "/" + file
      my_bucket.upload_file(path_to_file, "albums/"+ directory + "/" + file)
      print(f"Upload {file} in {directory}")
    except:
      print(f"Warning: This account don`t gave Access for upload photos in albums/")

def downloadPhotos(path, directory, my_bucket):
    for my_bucket_object in my_bucket.objects.filter(Prefix=f"albums/{directory}", Delimiter='.'):
      for object in my_bucket.objects.filter(Prefix=my_bucket_object.key):
        try:
          if object.key != my_bucket_object.key:
            my_bucket.download_file(object.key, path + "/" + object.key.split(my_bucket_object.key)[1])
            print(f"Download {object.key} in path directory")
          else:
            continue
        except:
          print(f"Warning: This account don`t gave Access for Download photos in albums/")


parser = argparse.ArgumentParser(description='Uploading photos to Yandex Object Storage.')
subparser = parser.add_subparsers(dest='command')
init = subparser.add_parser('init',
                    help='generate a settings file and create a bucket')
list_arg = subparser.add_parser('list',
                    help='view the list of albums in the cloud storage')
upload = subparser.add_parser('upload',
                    help='send photos to cloud storage')
download = subparser.add_parser('download',
                    help='download photos from cloud storage')
delete = subparser.add_parser('delete',
                    help='delete album in cloud storage')
mksite = subparser.add_parser('mksite',
                    help='create site with albums')
delete.add_argument('album_name')
upload.add_argument('--album', type=str, required=True)
upload.add_argument('--path', type=str, default=".", required=False)
download.add_argument('--album', type=str, required=True)
download.add_argument('--path', type=str, default=".", required=False)
args = parser.parse_args()

if not args.command == 'init':
  os.path.exists(CONFIG_PATH) and os.access(CONFIG_PATH, os.R_OK)

  user_resource, config = initialize()

  keys = ("region", "aws_secret_access_key", "aws_access_key_id", "bucket", "endpoint_url")
  for option in keys:
    try:
        config.get("default", option)
    except NoOptionError:
        print(f'This key is missing: {option}')
        print(f"run command 'python3 cloudphoto.py init' for set this key")
        sys.exit(1)


# init
if args.command == 'init':
  init_bucket = input('Enter your bucket name:')
  init_aws_access_key_id = input('Enter your aws_access_key_id:')
  init_aws_secret_access_key = input('Enter your aws_secret_access_key:')

  config = configparser.ConfigParser()
  config['default'] = {'aws_secret_access_key': init_aws_secret_access_key,
                       'aws_access_key_id': init_aws_access_key_id,
                       'region': 'ru-central1',
                       'bucket': init_bucket,
                       'endpoint_url': 'https://storage.yandexcloud.net'}
  with open(CONFIG_PATH, 'w') as configfile:
    config.write(configfile)

  user_resource, config = initialize()

  have_bucket = False

  for bucket in user_resource.buckets.all():
      if bucket.name == config['default']['bucket']:
        have_bucket = True
        break
  if not have_bucket:
    user_pub_bucket = user_resource.Bucket(config['default']['bucket'])
    try:
      user_pub_bucket.create()
      print(f"Don`t found bucket with name: {config['default']['bucket']}. Create new bucket with name {config['default']['bucket']}")
      sys.exit(0)
    except:
      print("Warning: This account don`t gave Access for create bucket")
      sys.exit(1)
  sys.exit(0)


# list
if args.command == 'list':
  user_resource, config = initialize()
  my_bucket = user_resource.Bucket(config['default']['bucket'])

  result_arr = []
  if list(my_bucket.objects.filter(Prefix=f"albums/", Delimiter='.').limit(1)):
    for my_bucket_object in my_bucket.objects.filter(Prefix=f"albums/", Delimiter='.'):
      if my_bucket_object.key == f"albums/":
        continue

      result_arr.append(my_bucket_object.key.replace(f"albums/","").replace(f"/",""))

    if len(result_arr) == 0:
      print("Photo albums not found")
      sys.exit(1)
    else:
      for result in result_arr:
        print(result)
      sys.exit(0)
  else:
    print("Directory albums not found")
    sys.exit(1)


# download
if args.command == 'download':
  user_resource, config = initialize()
  my_bucket = user_resource.Bucket(config['default']['bucket'])

  if os.path.isdir(args.path) and os.access(args.path, os.R_OK):
    if list(my_bucket.objects.filter(Prefix=f"albums/{args.album}/").limit(1)):
      print(f"Found directory with name {args.album}")
      downloadPhotos(args.path, args.album, my_bucket)
      sys.exit(0)
    else:
      print(f"Not found {args.album} in albums")
      sys.exit(0)
  else:
    print(f"Warning: Photos not found in directory {args.path}")
    sys.exit(1)


# upload
if args.command == 'upload':
  user_resource, config = initialize()
  my_bucket = user_resource.Bucket(config['default']['bucket'])

  if os.path.isdir(args.path) and os.access(args.path, os.R_OK):
    if list(my_bucket.objects.filter(Prefix=f"albums/{args.album}/").limit(1)):
      print(f"Found directory with name {args.album}")
      uploadPhotos(args.path, args.album, my_bucket)
      sys.exit(0)
    else:
      print(f"Not found {args.album} in albums")
      try:
        directory_name = f"albums/{args.album}/"
        my_bucket.put_object(Key=directory_name)
      except:
        print(f"Warning: This account don`t gave Access for create directory in albums/")
        sys.exit(1)
      print(f"Create directory with name {args.album} in albums")
      uploadPhotos(args.path, args.album, my_bucket)
      sys.exit(0)
  else:
    print(f"Warning: Photos not found in directory {args.path}")
    sys.exit(1)


# delete
if args.command == 'delete':
  user_resource, config = initialize()
  my_bucket = user_resource.Bucket(config['default']['bucket'])
  if list(my_bucket.objects.filter(Prefix=f"albums/{args.album_name}/").limit(1)):
    objects_to_delete = []
    for obj in my_bucket.objects.filter(Prefix=f"albums/{args.album_name}/"):
        objects_to_delete.append({'Key': obj.key})

    my_bucket.delete_objects(
        Delete={
            'Objects': objects_to_delete
        }
    )
    print(f"Delete album with name {args.album_name}")
    sys.exit(0)
  else:
    print(f"Warning: Photo album not found {args.album_name}")
    sys.exit(1)


# mksite
if args.command == 'mksite':
  user_resource, config = initialize()
  my_bucket = user_resource.Bucket(config['default']['bucket'])

  try:
    my_bucket.Acl().put(ACL='public-read')
  except:
    print("Warning: This account don`t gave Access for make bucket public")
    sys.exit(1)

  # Настроим бакет как хостинг для сайта. Настраивать бакет будем от имени
  # сервисного аккаунта spr23-00-sa-admin.
  # Создадим ресурс для конфигурации хостинга.
  bucket_website = my_bucket.Website()
  # Зададим суффикс для индексного документа.
  index_document = {'Suffix': 'index.html'}
  # Зададим объект с HTML страницей для вывода, если будет ошибка 4XX.
  error_document = {'Key': 'error.html'}
  # Активируем конфигурацию.
  bucket_website.put(WebsiteConfiguration={'ErrorDocument': error_document, 'IndexDocument': index_document})
  html_error_content = f"""
    <!doctype html>
    <html>
        <head>
            <meta charset="utf-8" />
            <title>Фотоархив</title>
        </head>
    <body>
        <h1>Ошибка</h1>
        <p>Ошибка при доступе к фотоархиву. Вернитесь на <a href="index.html">главную страницу</a> фотоархива.</p>
    </body>
    </html>
  """

  list_albums = list(my_bucket.objects.filter(Prefix=f"albums/", Delimiter='.'))
  list_albums.pop(0)

  count = 1
  a = Airium()

  a('<!DOCTYPE html>')
  with a.html(lang='ru'):
    with a.head():
        a.meta(charset="utf-8")
        a.title(_t="Фотоархив")
    with a.body():
        a.h1(_t="Фотоархив")
        with a.ul():
          for album in list_albums:
            text = album.key[:-1].replace(f"albums/","")
            with a.li():
              a.a(href=f"album{count}.html",_t=f"{text}")
            count += 1

  html_index_content = str(a)

  count = 1
  albums_list = list(my_bucket.objects.filter(Prefix=f"albums/", Delimiter='.'))
  albums_list.pop(0)
  for i in albums_list:
    a = Airium()

    a('<!DOCTYPE html>')
    with a.html(lang='ru'):
      with a.head():
          a.meta(charset="utf-8")
          a.link(href='https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.css', rel='stylesheet', type="text/css")
          a.script(src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js")
          a.script(src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/galleria.min.js")
          a.script(src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.js")
      with a.body():
          with a.div():
            for my_bucket_object in my_bucket.objects.filter(Prefix=i.key):
              if my_bucket_object.key == i.key:
                continue
              alt_t = f"{my_bucket_object.key}"
              alt_t = alt_t.replace(f"{i.key}","")
              my_bucket_object.key
              a.img(src=f"{config['default']['endpoint_url']}/{my_bucket_object.bucket_name}/{my_bucket_object.key}", alt=alt_t, width="960px", height="540px", background="#000")
          with a.p().small():
            a("Вернуться на ")
            with a.a(href="index.html"):
              a("главную страницу")
            a("фотоархива")
      # Создадим ресурс для объекта с ключом index.html.
    html_photos_content = str(a)

    html_photos = my_bucket.Object(f'album{count}.html')
    # Заполним объект HTML странице. Обязательно укажем, что объект имеет тип 'text/html'.
    html_photos.put(Body=html_photos_content, ContentType='text/html')
    count += 1


  # exit()
  # Создадим ресурс для объекта с ключом index.html.
  html_index = my_bucket.Object('index.html')
  # Заполним объект HTML странице. Обязательно укажем, что объект имеет тип 'text/html'.
  html_index.put(Body=html_index_content, ContentType='text/html')

  html_error = my_bucket.Object('error.html')
  # Заполним объект HTML странице. Обязательно укажем, что объект имеет тип 'text/html'.
  html_error.put(Body=html_error_content, ContentType='text/html')
  # Сформируем ссылку на веб-сайт. Откроем в браузере.
  print(f"https://{my_bucket.name}.website.yandexcloud.net")
  sys.exit(0)
