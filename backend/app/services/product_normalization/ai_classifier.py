from __future__ import annotations

from dataclasses import dataclass

from .models import NormalizationDecision, ProductCandidate


@dataclass(frozen=True)
class CategoryProfile:
    category: str
    display_name: str
    hints: tuple[str, ...]


_CATEGORY_PROFILES: tuple[CategoryProfile, ...] = (
    CategoryProfile("energy_drink", "Energy Drink", ("red bull", "rb", "monster", "nocco", "celsius", "power king")),
    CategoryProfile("beer", "Öl", ("öl", "ol", "lager", "ipa", "starköl", "pilsner")),
    CategoryProfile("wine_spirits", "Vin & Sprit", ("vin", "prosecco", "cava", "vodka", "gin", "whisky", "rom", "tequila")),
    CategoryProfile("soft_drink", "Läsk", ("cola", "coca", "pepsi", "fanta", "sprite", "läsk", "lask", "tonic")),
    CategoryProfile("water", "Vatten", ("vatten", "mineralvatten", "loka", "ramlosa", "bubbelvatten")),
    CategoryProfile("juice_smoothie", "Juice & Smoothie", ("juice", "smoothie", "apelsinjuice", "brämhults", "tropicana", "shot")),
    CategoryProfile("coffee_tea", "Kaffe & Te", ("kaffe", "latte", "espresso", "cappuccino", "te", "chai", "islatte")),
    CategoryProfile("bakery", "Bröd & Bageri", ("bröd", "brod", "bulle", "croissant", "bagel", "kanelbulle", "fralla")),
    CategoryProfile("dairy", "Mejeri", ("mjölk", "mjolk", "fil", "yoghurt", "ost", "smör", "smör", "grädde", "gradde")),
    CategoryProfile("produce", "Frukt & Grönt", ("banan", "äpple", "apple", "tomat", "gurka", "sallad", "potatis", "avokado", "citron", "grönsaker")),
    CategoryProfile("meat", "Kött", ("kött", "kott", "kyckling", "färs", "fars", "bacon", "skinka", "korv", "entrecote")),
    CategoryProfile("seafood", "Fisk & Skaldjur", ("lax", "tonfisk", "räkor", "rakor", "fisk", "torsk", "sushi")),
    CategoryProfile("pantry", "Skafferi", ("pasta", "ris", "nudlar", "mjöl", "mjol", "krydda", "konserver", "bönor", "bonor", "olja", "sås", "sas")),
    CategoryProfile("frozen_food", "Fryst", ("fryst", "glass", "pizza", "dumplings", "wok", "frozen")),
    CategoryProfile("snacks", "Snacks", ("chips", "popcorn", "nötter", "notter", "snacks", "kex", "ostbågar", "ostbagar")),
    CategoryProfile("candy", "Godis", ("godis", "choklad", "lösgodis", "losgodis", "marabou", "godispåse", "lakrits", "tuggummi")),
    CategoryProfile("restaurant_takeaway", "Restaurang & Takeaway", ("pizza", "burger", "burgare", "sallad", "wolt", "foodora", "take away", "takeaway", "shawarma", "kebab", "lunch")),
    CategoryProfile("household", "Hushåll", ("toapapper", "hushållspapper", "soppåsar", "soppasar", "folie", "batteri", "glödlampa", "glodlampa")),
    CategoryProfile("cleaning", "Städ & Tvätt", ("tvättmedel", "tvattmedel", "diskmedel", "såpa", "sapa", "rengöring", "sköljmedel", "skoljmedel")),
    CategoryProfile("personal_care", "Personvård", ("schampo", "balsam", "deo", "deodorant", "tandkräm", "tandkram", "rakblad", "smink", "hudkräm", "hudkram")),
    CategoryProfile("pharmacy_health", "Apotek & Hälsa", ("alvedon", "ipren", "medicin", "vitamin", "plåster", "plaster", "apotek", "hostmedicin")),
    CategoryProfile("baby", "Baby", ("blöjor", "blojor", "välling", "valling", "barnmat", "napp", "baby")),
    CategoryProfile("pet_supplies", "Husdjur", ("hundmat", "kattmat", "sand", "godisben", "pet", "foder", "veterinär", "veterinar")),
    CategoryProfile("clothing_accessories", "Kläder & Accessoarer", ("tshirt", "jeans", "jacka", "skor", "mössa", "mossa", "klänning", "klaninng", "väska", "vaska")),
    CategoryProfile("electronics", "Elektronik", ("hörlurar", "horlurar", "laddare", "kabel", "mobilskal", "airpods", "usb", "adapter", "skärm")),
    CategoryProfile("office_school", "Kontor & Skola", ("penna", "block", "papper", "skrivare", "bläck", "black", "anteckningsbok", "lim")),
    CategoryProfile("home_garden", "Hem & Trädgård", ("blomma", "växt", "vaxt", "kruka", "jord", "möbel", "mobel", "gardin", "kudde")),
    CategoryProfile("transport", "Transport", ("sl", "buss", "tåg", "tag", "biljett", "taxi", "uber", "parkering", "bensin", "diesel")),
    CategoryProfile("automotive", "Bil & Fordon", ("spolarvätska", "spolarvatska", "motorolja", "däck", "dack", "biltvätt", "biltvatt")),
    CategoryProfile("fitness", "Träning", ("protein", "proteinbar", "kreatin", "gymkort", "pt", "träningsband", "traningsband")),
    CategoryProfile("entertainment", "Nöje", ("bio", "spel", "game", "steam", "xbox", "playstation", "konsert", "bok")),
    CategoryProfile("subscription_service", "Abonnemang", ("spotify", "netflix", "viaplay", "icloud", "youtube premium", "adobe", "gymkort", "storytel")),
    CategoryProfile("tobacco_nicotine", "Tobak & Nikotin", ("snus", "cigaretter", "cigg", "vape", "nikotin", "velo", "zyn", "loop")),
    CategoryProfile("travel", "Resa", ("hotell", "flight", "flyg", "airbnb", "resa", "bagage", "hostel")),
    CategoryProfile("gift_flowers", "Presenter & Blommor", ("present", "blommor", "flower", "gåva", "gava", "kort")),
)


def get_category_catalog() -> list[dict[str, str]]:
    return [
        {
            "category": profile.category,
            "display_name": profile.display_name,
        }
        for profile in _CATEGORY_PROFILES
    ]


def classify(candidate: ProductCandidate) -> NormalizationDecision | None:
    tokens = {token.lower() for token in candidate.tokens}
    tokens.update(token.lower() for token in candidate.ascii_tokens)
    base = f" {candidate.base_label.lower()} "

    best_profile: CategoryProfile | None = None
    best_score = 0
    best_hint: str | None = None

    for profile in _CATEGORY_PROFILES:
        score = 0
        matched_hint: str | None = None

        for hint in profile.hints:
            hint_lower = hint.lower()
            if " " in hint_lower:
                if hint_lower in base:
                    score += 4
                    matched_hint = hint
            elif hint_lower in tokens:
                score += 3
                matched_hint = hint
            elif f" {hint_lower} " in base:
                score += 2
                matched_hint = hint

        if score > best_score:
            best_score = score
            best_profile = profile
            best_hint = matched_hint

    if best_profile is None or best_score < 2:
        return None

    confidence = 0.62
    if best_score >= 6:
        confidence = 0.84
    elif best_score >= 4:
        confidence = 0.74

    return NormalizationDecision(
        normalized_name=candidate.cleaned_label.title(),
        category=best_profile.category,
        confidence=confidence,
        source="ai",
        rule_id=f"ai.semantics.{best_profile.category}.{(best_hint or 'generic').replace(' ', '_').lower()}",
    )