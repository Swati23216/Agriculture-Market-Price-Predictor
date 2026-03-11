def generate_css():
    styles = mongo.db.style_settings.find_one()
    css = f"""
    :root {{
        --primary: {styles['primary_color']};
        --background: {styles['background_color']};
        --font: {styles['font_family']};
        --
    }}
    body {{
        background: var(--background);
        font-family: var(--font);
    }}
    .btn-primary {{
        background: var(--primary);
    }}
    """
    with open('app/static/css/generated_style.css', 'w') as f:
        f.write(css)