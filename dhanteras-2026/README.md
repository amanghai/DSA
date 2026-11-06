# Dhanteras 2026 – Instagram Post (Nazakat Telecom × A&H Teleservices)

**Output:** `output/dhanteras_2026_post.jpg` (1080×1350, Instagram 4:5 portrait), plus a 2× PNG (`output/dhanteras_2026_post.png`).

## Assets
| Asset | Status |
|---|---|
| Nazakat Telecom logo | ✅ real logo (`assets/nazakat_logo.jpg`) |
| A&H Teleservices logo | ⚠️ placeholder text badge. Swap in the real logo with `--ah-logo` |
| Showroom photo | ⚠️ not provided. Pass `--photo` and the centre turns into a gold arch frame with the photo |

## Re-render
```bash
# one-time: fonts
mkdir -p /tmp/fonts && cd /tmp/fonts && npm init -y && npm i @fontsource/cinzel-decorative \
  @fontsource/cinzel @fontsource/yatra-one @fontsource/great-vibes @fontsource/montserrat
pip install playwright

python3 make_post.py --fonts /tmp/fonts                                   # current version
python3 make_post.py --fonts /tmp/fonts --photo showroom.jpg --ah-logo ah_logo.png
```

## Caption (Instagram)
```
✨ शुभ धनतेरस ✨
Is Dhanteras, ghar laaiye nayi khushiyaan aur naya smartphone! 📱🪔

Maa Lakshmi aur Bhagwan Dhanvantari aap sabke ghar laayein sukh, samriddhi aur arogya. 🙏

Since 1992 aapka bharosa. Is tyohaar par Nazakat Telecom aur A&H Teleservices ki taraf se aapko aur aapke parivaar ko dher saari shubhkamnayein.

📍 Defence Road, Mamun Cantt, Pathankot
💬 Dhanteras ki shopping ke liye showroom aaiye, ya DM / WhatsApp karein!

#HappyDhanteras #Dhanteras2026 #ShubhDhanteras #Diwali2026 #NazakatTelecom #AHTeleservices #Pathankot #MamunCantt #PathankotMobileShop #DhanterasShopping #NewPhone #Punjab #Gurdaspur #Dalhousie
```
Geotag: Pathankot, Punjab. Tag: Nazakat Telecom + A&H Teleservices accounts.
