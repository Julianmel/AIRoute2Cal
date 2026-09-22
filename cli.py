"""Interface de linha de comando (CLI) para o AIRoute2Cal."""

import argparse
import os
import sys
from dotenv import load_dotenv

from src.extractor import extract_timeline_from_image
from src.calendar_generator import generate_ics, generate_outlook_csv


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="AIRoute2Cal: Converte capturas da Linha do Tempo do Google Maps em eventos do Outlook."
    )
    parser.add_argument("image", help="Caminho da imagem de captura da Linha do Tempo (JPEG/PNG)")
    parser.add_argument(
        "--output-dir",
        "-o",
        default="./output",
        help="Diretório para salvar os arquivos gerados (padrão: ./output)",
    )
    parser.add_argument(
        "--date",
        "-d",
        help="Data de referência no formato YYYY-MM-DD caso a tela informe apenas 'Hoje'",
    )
    parser.add_argument(
        "--only-displacements",
        action="store_true",
        help="Gera arquivo contendo apenas os trajetos de carro (deslocamentos)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="gemini-3.6-flash",
        help="Modelo do Gemini a ser utilizado (padrão: gemini-3.6-flash)",
    )
    parser.add_argument(
        "--api-key",
        help="Chave de API do Gemini (ou defina a variável GEMINI_API_KEY no .env)",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.image):
        print(f"Erro: Arquivo '{args.image}' não encontrado.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Analisando imagem com IA ({args.model}): {args.image} ...")
    try:
        timeline = extract_timeline_from_image(
            args.image,
            api_key=args.api_key,
            default_date=args.date,
            model_name=args.model,
        )
    except Exception as e:
        print(f"[!] Erro durante o processamento da imagem: {e}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    clean_date = timeline.date.replace("-", "")

    print(f"[+] Sucesso! Data identificada: {timeline.date}")
    print(f"    - Deslocamentos: {len(timeline.displacements)} trajetos")
    print(f"    - Visitas/paradas: {len(timeline.visits)} locais")
    if timeline.total_km:
        print(f"    - Distância total: {timeline.total_km} km")

    # 1. Gera o arquivo ICS
    ics_filename = os.path.join(args.output_dir, f"deslocamentos_{clean_date}.ics")
    include_visits = not args.only_displacements
    ics_content = generate_ics(
        timeline,
        include_displacements=True,
        include_visits=include_visits,
    )
    with open(ics_filename, "w", encoding="utf-8") as f:
        f.write(ics_content)
    print(f"[✓] Arquivo iCalendar gerado: {ics_filename}")

    # 2. Gera o arquivo CSV do Outlook
    csv_filename = os.path.join(args.output_dir, f"deslocamentos_{clean_date}.csv")
    csv_content = generate_outlook_csv(
        timeline,
        include_displacements=True,
        include_visits=include_visits,
    )
    with open(csv_filename, "w", encoding="utf-8") as f:
        f.write(csv_content)
    print(f"[✓] Arquivo CSV Outlook gerado: {csv_filename}")


if __name__ == "__main__":
    main()
