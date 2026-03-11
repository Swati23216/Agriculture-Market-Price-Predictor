def generate_global_css(styles):
    css = f"""
    /* Auto-generated CSS - DO NOT EDIT DIRECTLY */
    :root {{
        --primary-color: {styles['colors']['primary']};
        --secondary-color: {styles['colors']['secondary']};
        --background: {styles['colors']['background']};
        --font-main: {styles['fonts']['main']};
        --font-heading: {styles['fonts']['heading']};
    }}
    
    body {{
        font-family: var(--font-main);
        background: var(--background);
        color: var(--primary-color);
    }}
    
    h1, h2, h3 {{
        font-family: var(--font-heading);
        color: var(--secondary-color);
    }}
    """
    
    css_path = os.path.join(current_app.static_folder, 'css', 'global.css')
    with open(css_path, 'w') as f:
        f.write(css)