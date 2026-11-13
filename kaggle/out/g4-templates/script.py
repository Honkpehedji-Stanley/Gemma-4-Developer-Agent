# Copie les gabarits de conversation et configs tokenizer des deux modèles Gemma 4 montés (CPU, sans GPU).
import glob, os, shutil
for f in glob.glob('/kaggle/input/models/**/*', recursive=True):
    b = os.path.basename(f)
    if b in ('chat_template.jinja', 'tokenizer_config.json', 'generation_config.json', 'chat_template.json'):
        tag = 'w4a16' if 'w4a16' in f else 'q40'
        shutil.copy(f, f'/kaggle/working/{tag}_{b}')
        print(f, os.path.getsize(f))
