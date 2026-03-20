import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import io, math, os, base64

# --- CONFIGURATION ---
BF_WIDTH, BF_HEIGHT = 288, 72
PREVIEW_SCALE = 3
BOX_WIDTH, BOX_HEIGHT = BF_WIDTH * PREVIEW_SCALE, BF_HEIGHT * PREVIEW_SCALE
FONT_DIR = "fonts"

if not os.path.exists(FONT_DIR):
    os.makedirs(FONT_DIR)

st.set_page_config(page_title="BF SplashCraft", layout="wide")

# --- SESSION STATE ---
if 'layers' not in st.session_state:
    st.session_state.layers = []
if 'selected_idx' not in st.session_state:
    st.session_state.selected_idx = 0

def get_available_fonts():
    return sorted([f for f in os.listdir(FONT_DIR) if f.lower().endswith(('.ttf', '.otf'))])

# --- RENDER LOGIC ---
def generate_osd_image(layers):
    canvas = Image.new("RGB", (BF_WIDTH, BF_HEIGHT), (0, 255, 0))
    for l in layers:
        sc, xp, yp, th = l.get('scale', 1.0), l.get('x', 0), -l.get('y', 0), l.get('th', 128)
        if l['type'] == 'text':
            txt = l.get('content', 'TEXT')
            try:
                f_p = os.path.join(FONT_DIR, l['font']) if l.get('font') else None
                font = ImageFont.truetype(f_p, int(32 * sc)) if f_p else ImageFont.load_default()
            except: font = ImageFont.load_default()
            
            c_rgb = (255, 255, 255) if l.get('core')=="White" else (0, 0, 0)
            o_rgb = (255, 255, 255) if l.get('out_col')=="White" else (0, 0, 0)
            d = ImageDraw.Draw(canvas)
            bbox = d.textbbox((0, 0), txt, font=font)
            tx, ty = (BF_WIDTH - (bbox[2]-bbox[0])) // 2 + xp, (BF_HEIGHT - (bbox[3]-bbox[1])) // 2 + yp
            
            if l.get('sh_count', 0) > 0:
                rad = math.radians(l.get('sh_a', 45))
                for s_i in range(1, l['sh_count'] + 1):
                    ox, oy = int(math.cos(rad) * l['sh_d'] * s_i), int(math.sin(rad) * l['sh_d'] * s_i)
                    d.text((tx+ox, ty+oy), txt, font=font, fill=o_rgb)

            if l.get('out_col') != "None":
                o_th = l.get('o_th', 2)
                for ox in range(-o_th, o_th+1):
                    for oy in range(-o_th, o_th+1):
                        if ox*ox + oy*oy <= o_th**2: d.text((tx+ox, ty+oy), txt, font=font, fill=o_rgb)
            
            d.text((tx, ty), txt, font=font, fill=c_rgb)
        
        elif l['type'] == 'image':
            img_rgba = l['content'].convert("RGBA")
            data = np.array(img_rgba)
            dist = np.linalg.norm(data[:, :, :3] - np.array(l.get('chr_c', (0,0,0))), axis=2)
            data[dist <= l.get('chr_t', 20)] = [0,0,0,0]
            img_p = Image.fromarray(data)
            ratio = min(BF_WIDTH/img_p.width, BF_HEIGHT/img_p.height) * sc
            img_p = img_p.resize((max(1, int(img_p.width*ratio)), max(1, int(img_p.height*ratio))), Image.NEAREST)
            temp = Image.new("RGBA", (BF_WIDTH, BF_HEIGHT), (0,0,0,0))
            temp.paste(img_p, ((BF_WIDTH-img_p.width)//2 + xp, (BF_HEIGHT-img_p.height)//2 + yp))
            gray, alpha = np.array(temp.convert("L")), np.array(temp.getchannel('A'))
            canvas.paste((0,0,0), (0,0), Image.fromarray(np.where((alpha > 128) & (gray <= th), 255, 0).astype('uint8')))
            canvas.paste((255,255,255), (0,0), Image.fromarray(np.where((alpha > 128) & (gray > th), 255, 0).astype('uint8')))
    return canvas

# --- UI STYLE ---
st.markdown(f"""
    <style>
    .stAlert {{ display: none !important; }}
    .import-box {{ background-color: #f1f5f9; border: 1px solid #cbd5e1; padding: 10px; border-radius: 8px; margin-bottom: 15px; }}
    .stSlider {{ margin-bottom: -20px !important; }}
    label {{ font-size: 11px !important; font-weight: 700 !important; color: #475569; }}
    .preview-container {{ display: flex; justify-content: center; background: #1e293b; padding: 20px; border-radius: 8px; margin-top: 20px; }}
    .preview-img {{ width: {BOX_WIDTH}px; height: {BOX_HEIGHT}px; image-rendering: pixelated; border: 2px solid white; }}
    
    /* Branding Styles */
    .brand-title {{ font-size: 24px; font-weight: 800; color: #0f172a; margin-bottom: -5px; }}
    .brand-subtitle {{ font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 20px; }}

    div[role="radiogroup"] > label[data-baseweb="radio"] {{
        background: #f8fafc; border: 1px solid #e2e8f0; padding: 5px 10px; border-radius: 4px; margin-right: 5px;
    }}
    div[role="radiogroup"] > label[aria-checked="true"] {{
        background: #0f172a !important; color: white !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: IMPORT ---
with st.sidebar:
    # --- BRANDING SECTION ---
    st.markdown('<div class="brand-title">BF SplashCraft</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">by Davide Rado</div>', unsafe_allow_html=True)
    
    st.markdown("## 📥 IMPORT")
    with st.container():
        st.markdown('<div class="import-box">', unsafe_allow_html=True)
        st.markdown("### 🖼️ Image Asset")
        new_img = st.file_uploader("Upload Image", type=['png','jpg','bmp'], key="img_scan", label_visibility="collapsed")
        if new_img:
            if st.button("⚡ ADD IMAGE LAYER", use_container_width=True, type="primary"):
                img = Image.open(new_img).convert("RGBA")
                st.session_state.layers.append({
                    'type':'image', 'content':img, 'name':new_img.name,
                    'x':0,'y':0,'scale':1.0, 'chr_c':img.getpixel((0,0))[:3],
                    'chr_t':20, 'th':128
                })
                st.session_state.selected_idx = len(st.session_state.layers)-1
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="import-box">', unsafe_allow_html=True)
        st.markdown("### 🔤 Custom Font")
        new_f = st.file_uploader("Upload Font", type=['ttf','otf'], key="font_scan", label_visibility="collapsed")
        if new_f:
            st.info(f"Ready: {new_f.name}")
            if st.button("⚡ INSTALL & APPLY", use_container_width=True, type="primary"):
                font_path = os.path.join(FONT_DIR, new_f.name)
                with open(font_path, "wb") as f:
                    f.write(new_f.getbuffer())
                if st.session_state.layers:
                    idx = st.session_state.selected_idx
                    if st.session_state.layers[idx]['type'] == 'text':
                        st.session_state.layers[idx]['font'] = new_f.name
                        st.session_state[f"font_sel_{idx}"] = new_f.name
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    if st.button("🗑️ Reset Font Library", use_container_width=True):
        for f in get_available_fonts(): os.remove(os.path.join(FONT_DIR, f))
        st.rerun()

# --- MAIN UI ---
c1, c2 = st.columns([1, 2])
with c1:
    st.subheader("Layer Stack")
    ca, cb = st.columns(2)
    if ca.button("+ NEW TEXT", use_container_width=True):
        f_list = get_available_fonts()
        st.session_state.layers.append({'type':'text','content':'NEW TEXT','x':0,'y':0,'scale':1.0,'sh_count':0,'sh_d':2,'sh_a':45,'core':'White','out_col':'Black','o_th':2,'font':f_list[0] if f_list else None, 'th':128})
        st.session_state.selected_idx = len(st.session_state.layers)-1
        st.rerun()
    if cb.button("DELETE LAYER", use_container_width=True) and st.session_state.layers:
        st.session_state.layers.pop(st.session_state.selected_idx)
        st.session_state.selected_idx = max(0, st.session_state.selected_idx - 1)
        st.rerun()

    if st.session_state.layers:
        def layer_format_func(i):
            l = st.session_state.layers[i]
            return f"L{i}: {l['content'][:8]}" if l['type'] == 'text' else f"L{i}: IMG"
        st.session_state.selected_idx = st.radio("Select Active Layer:", range(len(st.session_state.layers)), format_func=layer_format_func, index=st.session_state.selected_idx, horizontal=True)
        l = st.session_state.layers[st.session_state.selected_idx]
        idx = st.session_state.selected_idx
        st.markdown("---")
        st.markdown("### Geometry")
        l['scale'] = st.slider("Scale", 0.1, 5.0, float(l['scale']), key=f"scale_{idx}")
        l['x'] = st.slider("Position X", -150, 150, int(l['x']), key=f"x_{idx}")
        l['y'] = st.slider("Position Y", -80, 80, int(l['y']), key=f"y_{idx}")

with c2:
    if st.session_state.layers:
        idx = st.session_state.selected_idx
        l = st.session_state.layers[idx]
        if l['type'] == 'text':
            st.subheader("Text Settings")
            l['content'] = st.text_input("Display Text", l['content'], key=f"content_{idx}")
            cc1, cc2 = st.columns(2)
            fonts = get_available_fonts()
            if l['font'] not in fonts and fonts: l['font'] = fonts[0]
            l['font'] = cc1.selectbox("Active Font", fonts, index=fonts.index(l['font']) if l['font'] in fonts else 0, key=f"font_sel_{idx}")
            l['core'] = cc2.selectbox("Core Color", ["White", "Black"], index=0 if l['core']=="White" else 1, key=f"core_{idx}")
            st.markdown("### Outline & Shadows")
            o1, o2 = st.columns([1, 2])
            out_opts = ["Black", "White", "None"]
            l['out_col'] = o1.selectbox("Border Color", out_opts, index=out_opts.index(l['out_col']), key=f"out_col_{idx}")
            l['o_th'] = o2.slider("Border Thickness", 0, 10, int(l['o_th']), key=f"o_th_{idx}")
            s1, s2, s3 = st.columns(3)
            l['sh_count'] = s1.slider("Shadow Levels", 0, 5, int(l['sh_count']), key=f"sh_count_{idx}")
            l['sh_d'] = s2.slider("Offset Distance", 0, 15, int(l['sh_d']), key=f"sh_d_{idx}")
            l['sh_a'] = s3.slider("Angle (°)", 0, 360, int(l['sh_a']), key=f"sh_a_{idx}")
        elif l['type'] == 'image':
            st.subheader("Image Settings")
            cc1, cc2 = st.columns([1, 2])
            cp = cc1.color_picker("Chroma Key", '#%02x%02x%02x' % l['chr_c'], key=f"chr_c_{idx}")
            l['chr_c'] = tuple(int(cp.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            l['chr_t'] = cc2.slider("Tolerance", 0, 150, int(l['chr_t']), key=f"chr_t_{idx}")
            l['th'] = st.slider("B&W Threshold", 0, 255, int(l['th']), key=f"th_{idx}")

# --- PREVIEW ---
st.divider()
img_out = generate_osd_image(st.session_state.layers)
buf = io.BytesIO()
img_out.resize((BOX_WIDTH, BOX_HEIGHT), resample=Image.NEAREST).save(buf, format="PNG")
st.markdown(f'<div class="preview-container"><img src="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}" class="preview-img"></div>', unsafe_allow_html=True)

# --- EXPORT BUTTON ---
btn_buf = io.BytesIO()
img_out.save(btn_buf, format="BMP")
st.download_button(
    label="💾 EXPORT AS .BMP", 
    data=btn_buf.getvalue(), 
    file_name="splash.bmp", 
    mime="image/bmp", 
    use_container_width=True,
    type="primary"
)
