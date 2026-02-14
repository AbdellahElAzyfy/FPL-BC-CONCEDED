import asyncio
import aiohttp
from understat import Understat
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
import os
import json

# --- 1. CONFIGURATION ---
TEAMS_25_26 = [
    "Arsenal", "Aston_Villa", "Bournemouth", "Brentford", "Brighton",
    "Burnley", "Chelsea", "Crystal_Palace", "Everton", "Fulham",
    "Leeds", "Liverpool", "Manchester_City", "Manchester_United",
    "Newcastle_United", "Nottingham_Forest", "Sunderland", "Tottenham",
    "West_Ham", "Wolverhampton_Wanderers"
]

# Specific colors for every position
# Specific colors for every position
COLOR_MAP = {
    # Strikers
    'ST': '#00ff85', 'FW': '#00ff85', 'S': '#00ff85',
    # Wingers
    'LW': '#ff003c', 'AML': '#ff003c', 'ML': '#ff003c', 'FWL': '#ff003c',
    'RW': '#00d4ff', 'AMR': '#00d4ff', 'MR': '#00d4ff', 'FWR': '#00d4ff',
    # Midfield
    'CAM': '#9146ff', 'AMC': '#9146ff', 'CM': '#ffa500', 'MC': '#ffa500',
    'DMC': '#ffa500', 'DM': '#ffa500', 'M': '#ffa500',
    # Defense
    'CB': '#ffffff', 'DC': '#ffffff',
    'LB': '#fcf305', 'DL': '#fcf305', 'DML': '#fcf305',
    'RB': '#ff69b4', 'DR': '#ff69b4', 'DMR': '#ff69b4',
    'GK': '#777777',
    'Unknown': '#888888'
}

# Aggregated legend categories (label -> set of position aliases + color)
# Ensures counts reflect common aliases returned by APIs and overrides
LEGEND_CATEGORIES = {
    'ST': {
        'positions': {'ST', 'FW', 'S'},
        'color': '#00ff85'
    },
    'LW': {
        'positions': {'LW', 'AML', 'ML', 'FWL'},
        'color': '#ff003c'
    },
    'RW': {
        'positions': {'RW', 'AMR', 'MR', 'FWR'},
        'color': '#00d4ff'
    },
    'CAM': {
        'positions': {'CAM', 'AMC'},
        'color': '#9146ff'
    },
    'CM': {
        'positions': {'CM', 'MC', 'DMC', 'DM', 'M'},
        'color': '#ffa500'
    },
    'CB': {
        'positions': {'CB', 'DC'},
        'color': '#ffffff'
    },
    'LB': {
        'positions': {'LB', 'DL', 'DML'},
        'color': '#fcf305'
    },
    'RB': {
        'positions': {'RB', 'DR', 'DMR'},
        'color': '#ff69b4'
    }
}

# Manual position overrides for cases where APIs return ambiguous/empty data
MANUAL_POSITION_OVERRIDE = {
    'brian brobbey': 'FW',
    'donyell malen': 'FW',
    'emiliano buendía': 'RW',
    'emiliano buendia': 'RW',
    'john mcginn': 'CM'
}

# ID-based overrides to apply globally across teams
ID_POSITION_OVERRIDE = {
    '731717': 'RW',   # Anthony Elanga
    '732713': 'RW',   # Brajan Gruda
    '734525': 'FW',   # William Osula
    '734545': 'RW',   # Rio Ngumoha
    '734829': 'FW',   # Tyrique George
    '735707': 'RW',   # Oscar Bobb
    '736206': 'CM',   # Jefferson Lerma
    '736880': 'RW',   # Jacob Murphy
    '737014': 'AMC',  # Brenden Aaronson
    '737168': 'RW',   # Mohammed Kudus
    '738574': 'LB',   # Tyrick Mitchell
    '738598': 'CM',   # Marshall Munetsi
    '740621': 'LB',   # Maxim De Cuyper
    '740665': 'AMC',  # Brenden Aaronson
    '740682': 'FW',   # Eli Junior Kroupi
    '741324': 'RW',   # Emiliano Buendia variant
    '742051': 'LW',   # Ryan Sessegnon
    '742132': 'FW',   # Noah Okafor
    '742406': 'RW',   # Bukayo Saka variant
    '742432': 'RW',   # Amad Diallo Traore
    '742601': 'RW',   # Estevao
    '742996': 'FW',   # Beto
    '743044': 'CM',   # Chimuanya Ugochukwu
    '743830': 'FW',   # Igor Jesus
    '743848': 'FW',   # Marc Guiu
    '744491': 'LW',   # Leandro Trossard variant
    '744492': 'LW',   # Gabriel Martinelli
    '745558': 'AMC',  # Brenden Aaronson variant
    '745560': 'FW',   # Noah Okafor variant
    '745934': 'RW',   # Jacob Murphy
    '746596': 'LW',   # Leandro Trossard variant
    '746633': 'RW',   # Jadon Sancho
    '746658': 'RW',   # Jhon Arias
    '746677': 'FW',   # Lyle Foster
    '746991': 'FW',   # Richarlison
    '748330': 'RW',   # Bukayo Saka variant
    '748380': 'RW',   # Samuel Chukwueze
    '748609': 'LW',   # Jamie Bynoe-Gittens
    '748997': 'CM',   # Tomas Soucek variant
    '750175': 'FW',   # Beto variant
    '750205': 'CM',   # Tomas Soucek
    '750207': 'RB',   # Kyle Walker-Peters
    '750392': 'FW',   # Brian Brobbey
    '750544': 'FW',   # Marc Guiu
    '751972': 'FW',   # Enes Unal variant
    '752061': 'RW',   # Jhon Arias variant
    '752069': 'RB',   # Daniel Munoz variant
    '754483': 'FW',   # Stefanos Tzimas
    '754948': 'RW',   # Phil Foden
    '755086': 'RW',   # Noni Madueke
    '755091': 'RW',   # Bukayo Saka variant
    '755120': 'FW',   # Armando Broja
    '755129': 'RB',   # Daniel Munoz
    '755199': 'FW',   # Donyell Malen
    '755292': 'FW',   # Wilson Isidor
    '755361': 'LB',   # Diogo Dalot
    '755637': 'RW',   # Emiliano Buendia
    '755638': 'FW',   # Donyell Malen (variant)
    '755650': 'RW',   # Bukayo Saka
    '755653': 'LW',   # Leandro Trossard
    '756008': 'LW',   # Anthony Gordon
    '756025': 'FW',   # Zian Flemming
    '756044': 'CM',   # Pape Sarr
    '756605': 'FW',   # Charalampos Kostoulas
    '758663': 'RW',   # Amad Diallo Traore variant
    '758686': 'FW',   # Eli Junior Kroupi variant
    '758689': 'RW',   # David Brooks
    '758822': 'LW',   # Anthony Gordon variant
    '759052': 'FW',   # Armando Broja
    '759098': 'LW',   # Savio
    '759141': 'LW',   # Keane Lewis-Potter
    '759143': 'LW',   # Kevin Schade
    '759144': 'LW',   # Mikkel Damsgaard
    '759311': 'FW',   # Richarlison variant
    '759328': 'FW',   # Alexander Isak
    '759386': 'LW',   # Leandro Trossard variant
    '760052': 'LW',   # Leandro Trossard variant
    '760101': 'LW',   # Justin Kluivert
    '760249': 'FW',   # Ollie Watkins
    '760333': 'RB',   # Jayden Bogle
    '760505': 'RW',   # Marcus Edwards
    '760520': 'LW',   # Harvey Barnes
    '760524': 'RW',   # Jacob Murphy variant
    '760555': 'FW',   # Enes Unal
    '760592': 'FW',   # placeholder
    '760624': 'RW',   # Bukayo Saka variant
    '760626': 'LW',   # Leandro Trossard variant
    '760643': 'FW',   # Donyell Malen (variant)
    '760646': 'CM',   # John McGinn
    '760702': 'RB',   # Timothy Castagne
    '760787': 'RW'    # Jeremy Doku
}

# --- 2a. HELPERS ---


def normalize_position_code(pos_val):
    """Normalize raw position codes from the API/rosters."""
    if not pos_val:
        return None
    if isinstance(pos_val, str):
        pos = pos_val.strip().upper().replace('-', '')
        # Understat sometimes returns things like "Sub"; treat as unknown
        if pos in {'SUB', 'S', '??', ''}:
            return None
        return pos
    return None


async def safe_get_player_history(understat, player_id, name=None, retries=2):
    """Fetch player grouped stats with retries and safe JSON handling."""
    for attempt in range(retries):
        try:
            return await understat.get_player_grouped_stats(player_id)
        except (json.JSONDecodeError, aiohttp.ContentTypeError) as e:
            print(
                f"DEBUG: Malformed response for {name or player_id}: {e}; attempt {attempt + 1}/{retries}")
        except Exception as e:
            print(
                f"DEBUG: Exception fetching history for {name or player_id}: {e}; attempt {attempt + 1}/{retries}")
    return None

# --- 2. DATA ENGINE ---


async def get_team_data(team_name):
    def extract_main_pos(history, player_name=None):
        # Try to extract from multiple sources
        if not history:
            return None

        def first_valid(pos_val):
            if not pos_val:
                return None
            if isinstance(pos_val, str):
                pos_code = pos_val.split()[0] if ' ' in pos_val else pos_val
                if pos_code and pos_code not in ['Sub', 'S', '??', '']:
                    return pos_code
            if isinstance(pos_val, dict):
                # Understat sometimes returns {season: {role: {...}}}
                for _, role_dict in pos_val.items():
                    if isinstance(role_dict, dict):
                        role_pos = role_dict.get('position')
                        if isinstance(role_pos, str):
                            role_code = role_pos.split(
                            )[0] if ' ' in role_pos else role_pos
                            if role_code and role_code not in ['Sub', 'S', '??', '']:
                                return role_code
            return None

        # First check top-level position field (common in player stats)
        pos_top = history.get('position')
        pos_val = first_valid(pos_top)
        if pos_val:
            return pos_val

        # Try all season entries, prioritizing most recent
        seasons = history.get('season', [])
        if seasons:
            for entry in seasons:
                pos_val = first_valid(entry.get('position', ''))
                if pos_val:
                    return pos_val

        # Try career aggregate
        career = history.get('career', {})
        pos_val = first_valid(career.get('position'))
        if pos_val:
            return pos_val

        # Debug log for persistent failures
        if player_name:
            print(
                f"DEBUG: Could not extract position for {player_name}, history keys: {history.keys()}, position value: {history.get('position', 'N/A')}")

        return None

    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        matches = await understat.get_team_results(team_name, 2025)
        all_shots = []
        pos_cache = {}
        unknown_positions = []

        for match in matches:
            match_id = match['id']
            shots = await understat.get_match_shots(match_id)
            rosters = await understat.get_match_players(match_id)

            is_home = match['h']['title'].replace(" ", "_") == team_name
            side = 'a' if is_home else 'h'

            # Build player lookup tables for this side
            p_data = {}
            name_to_id = {}
            id_to_pos = {}
            if side in rosters:
                for p_id, p_info in rosters[side].items():
                    name = p_info.get('player_name') or p_info.get('player')
                    pos_val = normalize_position_code(
                        p_info.get('position')) or '??'
                    if name:
                        p_data[name] = {'id': p_id, 'pos': pos_val}
                        name_to_id[name] = p_id
                    id_to_pos[p_id] = pos_val

            # Build a substitution map: sub_player_id -> original_player_position
            sub_position_map = {}
            try:
                match_events = await understat.get_match_events(match_id)
                subs = match_events.get(
                    'substitutions', []) if match_events else []
                for sub_event in subs:
                    player_in = sub_event.get('player_in')
                    player_out = sub_event.get('player_out')
                    if not player_in or not player_out:
                        continue

                    out_id = name_to_id.get(player_out)
                    if not out_id and player_out in id_to_pos:
                        out_id = player_out
                    out_pos = id_to_pos.get(out_id)
                    if out_pos and out_pos not in ['Sub', 'S', '??']:
                        in_id = name_to_id.get(player_in)
                        if not in_id and player_in in id_to_pos:
                            in_id = player_in
                        if in_id:
                            sub_position_map[in_id] = out_pos
            except Exception:
                pass

            for shot in shots[side]:
                if float(shot['xG']) >= 0.3:
                    name = shot['player']
                    info = p_data.get(name, {'id': None, 'pos': '??'})
                    p_id, pos = info['id'], info['pos']

                    # Fallback: resolve player id/pos from lookup if missing
                    if p_id is None and name in name_to_id:
                        p_id = name_to_id[name]
                        pos = id_to_pos.get(p_id, '??')

                    # Log what position we got from roster
                    original_pos = pos

                    # Check if position is unmapped (not in COLOR_MAP) or unknown
                    pos = normalize_position_code(pos) or '??'

                    # ID-based override early to avoid unnecessary network calls
                    if p_id and str(p_id) in ID_POSITION_OVERRIDE:
                        pos = ID_POSITION_OVERRIDE[str(p_id)]

                    needs_resolution = pos in ['??'] or not COLOR_MAP.get(pos)

                    if needs_resolution:
                        # First check if we have a substitution position for this player
                        if p_id and p_id in sub_position_map:
                            pos = normalize_position_code(
                                sub_position_map[p_id]) or pos
                        elif p_id:
                            if p_id not in pos_cache:
                                history = await safe_get_player_history(
                                    understat, p_id, name=name)
                                extracted_pos = extract_main_pos(
                                    history, name) if history else None
                                if extracted_pos:
                                    pos = normalize_position_code(
                                        extracted_pos) or pos
                                    pos_cache[p_id] = pos
                                else:
                                    pos_cache[p_id] = None
                            else:
                                cached = pos_cache.get(p_id)
                                if cached:
                                    pos = cached

                        # Fallback to roster-listed position if still unresolved
                        if (not COLOR_MAP.get(pos)) and p_id and p_id in id_to_pos:
                            roster_pos = normalize_position_code(
                                id_to_pos[p_id])
                            if roster_pos and COLOR_MAP.get(roster_pos):
                                pos = roster_pos

                        # Last resort: search by name if still unknown
                        if not COLOR_MAP.get(pos) and name:
                            name_key = f"name_{name}"
                            if name_key not in pos_cache:
                                try:
                                    # Try league-specific player search
                                    league_players = await understat.get_league_players('EPL', 2025)
                                    for player in league_players:
                                        if player.get('player_name', '').lower() == name.lower():
                                            player_id = player.get('id')
                                            if player_id:
                                                history = await understat.get_player_grouped_stats(player_id)
                                                extracted_pos = extract_main_pos(
                                                    history, name)
                                                if extracted_pos:
                                                    pos = extracted_pos
                                                    pos_cache[name_key] = pos
                                                    break
                                except Exception as e:
                                    print(
                                        f"DEBUG: Name search failed for {name}: {e}")
                            elif pos_cache.get(name_key):
                                pos = pos_cache[name_key]

                    # Manual override as final fallback
                    if not COLOR_MAP.get(pos):
                        # First try ID-based override (again, after normalization)
                        if p_id and str(p_id) in ID_POSITION_OVERRIDE:
                            pos = ID_POSITION_OVERRIDE[str(p_id)]
                        elif name:
                            override_pos = MANUAL_POSITION_OVERRIDE.get(
                                name.lower())
                            if override_pos:
                                pos = override_pos

                    # Skip goalkeepers; keep others, tagging unmapped as Unknown
                    if pos in ['GK', 'Goalkeeper']:
                        continue
                    color = COLOR_MAP.get(pos)
                    if not color:
                        pos = 'Unknown'
                        color = COLOR_MAP['Unknown']
                        unknown_positions.append({
                            'player': name,
                            'id': p_id,
                            'match': match_id,
                            'original_pos': original_pos,
                            'final_pos': pos
                        })

                    # Flip Y to align Understat orientation with StatsBomb pitch (avoids swapped wings)
                    all_shots.append({
                        'x': float(shot['X']) * 120, 'y': (1 - float(shot['Y'])) * 80,
                        'xg': float(shot['xG']), 'pos': pos,
                        'color': color
                    })
        if unknown_positions:
            print(f"Unknown positions for {team_name}: {unknown_positions}")
        return pd.DataFrame(all_shots)

# --- 3. VISUAL ENGINE ---


def create_pitch_map(df, team_name):
    pitch = VerticalPitch(pitch_type='statsbomb', half=True,
                          pitch_color='#121212', line_color='#555555')
    fig, ax = pitch.draw(figsize=(12, 12))
    fig.set_facecolor('#121212')

    # Smaller circle sizes for clearer separation
    sizes = df['xg'] * 180

    sc = pitch.scatter(df.x, df.y, s=sizes, c=df.color,
                       edgecolors='white', linewidth=0.8, alpha=0.9, ax=ax, zorder=3)

    # Title & Stats
    plt.title(f'          {team_name.replace("_", " ")}\nBig Chances Conceded | 2025/26',
              color='white', fontsize=22, fontweight='bold', pad=80)

    ax.text(90, 40, f'BC CONCEDED: {len(df)}', color='white', fontsize=12, fontweight='bold',
            bbox=dict(facecolor='#121212', edgecolor='#00ff85', boxstyle='round,pad=0.5'))

    # THE COLOR GUIDE (Legend) with counts per position category
    # Aggregate counts across common aliases
    counts_by_cat = {}
    if 'pos' in df.columns:
        for cat, info in LEGEND_CATEGORIES.items():
            positions = info['positions']
            counts_by_cat[cat] = int(df['pos'].isin(positions).sum())

    legend_elements = []
    for cat, info in LEGEND_CATEGORIES.items():
        count = counts_by_cat.get(cat, 0)
        label = f"{cat} ({count})"
        legend_elements.append(mpatches.Patch(
            color=info['color'], label=label))

    # Place legend below the pitch
    ax.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, -0.18),
              ncol=4, facecolor='#121212', edgecolor='#555555', labelcolor='white', fontsize=10)

    # Move the size guide text to the side (no circles over the pitch)
    fig.text(0.8, 0.72, "Chance Quality (xG)", color='white', fontsize=10,
             fontweight='bold', ha='left')
    fig.text(0.8, 0.69, "Larger circle = higher xG", color='#00ff85', fontsize=9,
             ha='left')

    # Add club badge (top-left) and personal logo (bottom-right)
    def add_image(ax_handle, path, xy, zoom=0.12):
        if not os.path.exists(path):
            return
        img = mpimg.imread(path)
        ab = AnnotationBbox(OffsetImage(img, zoom=zoom), xy,
                            xycoords='axes fraction', frameon=False, box_alignment=(0.5, 0.5))
        ax_handle.add_artist(ab)

    badge_map = {
        'Leeds_United': 'Leeds.png'
    }
    badge_file = badge_map.get(team_name, f"{team_name}.png")
    badge_path = os.path.join('images', 'badges', badge_file)
    add_image(ax, badge_path, (0.08, 0.9), zoom=0.14)

    logo_path = os.path.join('images', 'Logo.png')
    add_image(ax, logo_path, (0.92, 0.08), zoom=0.12)

    # Save
    filename = f"{team_name}_Tactical_Map.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    for team in TEAMS_25_26:
        try:
            df_team = asyncio.run(get_team_data(team))
            if not df_team.empty:
                create_pitch_map(df_team, team)
                print(f"✅ Created map for {team}")
        except Exception as e:
            print(f"❌ Error for {team}: {e}")
