import sys
import os
import json
import re

TXT_DIR = sys.argv[1]
JSON_PATH = sys.argv[2]


def parse_list_file(path):
    """
    Parse a TXT file with this structure:
      Nombre: Category
      Nombre: SeriesName
      genero: ...
      descripción: ...
      anio: ...
      iconPng: ...
      icono: ...
      logohorizontal: ...
      temporadas
      nombre: Temporada 1
      tmbdid: 12697          <- optional season-line-level tmdb id or global
      01 Episode Title
      https://url_to_episode
      02 Another Title
      https://url_to_episode2
      nombre: Temporada 2
      ...

    Returns dict { 'categorias': [ { 'nombre': category, 'series': [ { ... } ] } ] }
    """
    # Read all non-empty lines
    with open(path, 'r', encoding='utf-8') as f:
        raw = [l.strip() for l in f if l.strip()]
    lines = raw

    # Category name (first line)
    if not lines or not lines[0].lower().startswith('nombre:'):
        raise ValueError('Missing category name')
    category_name = lines[0].split(':',1)[1].strip()

    # Series name (second line)
    if len(lines) < 2 or not lines[1].lower().startswith('nombre:'):
        raise ValueError('Missing series name')
    serie_name = lines[1].split(':',1)[1].strip()

    # Metadata up to 'temporadas'
    metadata = {}
    idx = 2
    while idx < len(lines) and lines[idx].lower() != 'temporadas':
        if ':' in lines[idx]:
            key, val = lines[idx].split(':',1)
            metadata[key.strip().lower()] = val.strip()
        idx += 1

    # Skip 'temporadas' marker
    if idx < len(lines) and lines[idx].lower() == 'temporadas':
        idx += 1

    seasons = []
    # Identify season header indices
    season_idxs = [i for i, l in enumerate(lines[idx:], start=idx) if l.lower().startswith('nombre:')]
    season_idxs.append(len(lines))  # end bound

    # Parse each season
    for s in range(len(season_idxs)-1):
        start = season_idxs[s]
        end = season_idxs[s+1]
        # Season header line
        season_line = lines[start]
        season_name = season_line.split(':',1)[1].strip()
        num_match = re.search(r"\d+", season_name)
        season_num = int(num_match.group()) if num_match else s+1
        
        # Check if next line is tmdbid
        season_tmdb = None
        ep_start = start + 1
        if ep_start < end and lines[ep_start].lower().startswith('tmbdid:'):
            season_tmdb = lines[ep_start].split(':',1)[1].strip()
            ep_start += 1

        # Parse episodes: expect pairs of (NN Title, URL)
        capitulos = []
        i = ep_start
        while i < end:
            m = re.match(r"(\d+)\s+(.*)", lines[i])
            if m:
                numero = int(m.group(1))
                titulo = m.group(2).strip()
                url = lines[i+1].strip() if (i+1) < end else ''
                capitulos.append({'numero': numero, 'titulo': titulo, 'url': url})
                i += 2
            else:
                i += 1

        seasons.append({
            'nombre': season_name,
            'numero_temporada': season_num,
            'capitulos': capitulos
        })

        # If season-level tmdb provided, store in metadata for series
        if season_tmdb:
            metadata['tmdb_id'] = season_tmdb

    # Build series dict
    serie = {
        'nombre': serie_name,
        'genero': metadata.get('genero',''),
        'descripcion': metadata.get('descripción', metadata.get('descripcion','')),
        'anio': metadata.get('anio',''),
        'iconPng': metadata.get('iconpng',''),
        'icono': metadata.get('icono',''),
        'logoHorizontal': metadata.get('logohorizontal',''),
        'temporadas': seasons,
        'total_seasons': len(seasons),
        'tmdb_id': metadata.get('tmdb_id','')
    }

    return {'categorias': [{ 'nombre': category_name, 'series': [serie] }]}


def load_catalog(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'categorias': []}


def save_catalog(path, catalog):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=4)


def merge_catalog(base, nuevo):
    for new_cat in nuevo.get('categorias', []):
        existing = next((c for c in base['categorias'] if c['nombre']==new_cat['nombre']), None)
        if not existing:
            base['categorias'].append(new_cat)
        else:
            for ns in new_cat['series']:
                if not any(s['nombre']==ns['nombre'] for s in existing['series']):
                    existing['series'].append(ns)
    return base


def main():
    catalog = load_catalog(JSON_PATH)
    for fname in os.listdir(TXT_DIR):
        if not fname.lower().endswith('.txt'):
            continue
        data = parse_list_file(os.path.join(TXT_DIR, fname))
        catalog = merge_catalog(catalog, data)
    save_catalog(JSON_PATH, catalog)


if __name__ == '__main__':
    main()
