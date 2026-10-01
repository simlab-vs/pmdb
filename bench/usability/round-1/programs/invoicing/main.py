"""Prints the invoices of the orders stored in a JSON file."""

import json
import sys

from billing import format_cents, invoice


def main(path):
  with open(path) as f:
    orders = json.load(f)

  for order in orders:
    inv = invoice(order)
    print(f"order {order['id']} ({inv['currency']})")
    for row in inv["rows"]:
      print(f"  {row['sku']:<10} net {format_cents(row['net']):>10}  tax {format_cents(row['tax']):>9}")
    print(f"  total {format_cents(inv['total'])} (net {format_cents(inv['net'])}, tax {format_cents(inv['tax'])})")


if __name__ == "__main__":
  main(sys.argv[1])
