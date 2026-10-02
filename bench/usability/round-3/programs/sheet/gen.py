"""Generates random inputs for the sheet program (hidden from agents)."""

import random

COLUMNS = "ABCDEFGH"


def address(column, row):
  return f"{COLUMNS[column]}{row}"


class FormulaMaker:
  def __init__(self, rng, data_rows, data_cols):
    self.rng = rng
    self.data_rows = data_rows
    self.data_cols = data_cols
    self.earlier = []

  def number(self):
    rng = self.rng
    return rng.choice([str(rng.randint(0, 9)), str(rng.randint(1, 100)), f"{rng.randint(0, 99)}.{rng.randint(1, 99)}"])

  def data_ref(self):
    rng = self.rng
    return "Data!" + address(rng.randrange(self.data_cols), rng.randint(1, self.data_rows))

  def data_range(self):
    rng = self.rng
    c1 = rng.randrange(self.data_cols)
    c2 = min(self.data_cols - 1, c1 + rng.randint(0, 2))
    r1 = rng.randint(1, self.data_rows)
    r2 = min(self.data_rows + rng.choice([0, 0, 0, 2]), r1 + rng.randint(0, 6))
    return f"Data!{address(c1, r1)}:{address(c2, r2)}"

  def ref(self):
    rng = self.rng
    if self.earlier and rng.random() < 0.6:
      sheet, name = rng.choice(self.earlier[-12:])
      return f"{sheet}!{name}" if rng.random() < 0.3 or sheet != self.sheet else name
    return self.data_ref()

  def expr(self, depth):
    rng = self.rng
    if depth <= 0:
      return rng.choice([self.number, self.ref, self.ref, self.ref])()
    kind = rng.choices(
      ["leaf", "binary", "agg", "round", "if", "iferror", "countif", "sumif", "abs", "mod", "pct", "paren", "text"],
      [4, 8, 4, 2, 2, 1, 1, 1, 1, 1, 1, 2, 0.15])[0]
    sub = lambda: self.expr(depth - 1)
    if kind == "leaf":
      return self.expr(0)
    if kind == "binary":
      op = rng.choice(["+", "+", "-", "*", "/", "^", "&"] if rng.random() < 0.03 else ["+", "+", "-", "*", "/"])
      if op == "^":
        return f"{sub()}^{rng.randint(0, 3)}"
      return f"{sub()}{op}{sub()}"
    if kind == "agg":
      name = rng.choice(["SUM", "SUM", "AVG", "AVERAGE", "MIN", "MAX", "COUNT"])
      args = [self.data_range()]
      if rng.random() < 0.4:
        args.append(sub())
      return f"{name}({', '.join(args)})"
    if kind == "round":
      return f"ROUND({sub()}, {rng.choice([0, 1, 2, 2, 3, -1])})"
    if kind == "if":
      cond = f"{sub()}{rng.choice(['>', '<', '>=', '<=', '=', '<>'])}{sub()}"
      if rng.random() < 0.15:
        cond = f"{rng.choice(['AND', 'OR'])}({cond}, {sub()}>{self.number()})"
      if rng.random() < 0.05:
        cond = f"NOT({cond})"
      elif rng.random() < 0.04:
        cond = rng.choice(["TRUE", "FALSE", sub()])
      return f"IF({cond}, {sub()}, {sub()})"
    if kind == "iferror":
      return f"IFERROR({sub()}, {self.number()})"
    if kind == "countif":
      return f'COUNTIF({self.data_range()}, "{rng.choice([">", "<", ">=", "<=", "<>", ""])}{rng.randint(0, 60)}")'
    if kind == "sumif":
      if rng.random() < 0.2:
        return f'SUMIF({self.data_range()}, "<{rng.randint(0, 50)}", {self.data_range()})'
      return f'SUMIF({self.data_range()}, ">{rng.randint(0, 50)}")'
    if kind == "abs":
      return f"ABS({sub()})"
    if kind == "mod":
      return f"MOD({sub()}, {rng.choice(['3', '7', '10', self.ref()])})"
    if kind == "pct":
      return f"{self.number()}%*{sub()}"
    if kind == "text":
      if rng.random() < 0.5:
        return f'LEN(CONCAT({sub()}, "-", {self.ref()}))'
      return f"LEN({sub()}&{self.ref()})"
    return f"({sub()})"


def generate(seed):
  rng = random.Random(seed)
  data_rows = rng.randint(6, 20)
  data_cols = rng.randint(3, 6)
  data = {}
  for r in range(1, data_rows + 1):
    for c in range(data_cols):
      roll = rng.random()
      if roll < 0.06:
        continue
      if roll < 0.09:
        data[address(c, r)] = rng.choice(["n/a", "pending", "'42", "'7.5", "x"])
      elif roll < 0.10:
        data[address(c, r)] = rng.choice(["TRUE", "FALSE"])
      elif roll < 0.16:
        data[address(c, r)] = "0"
      else:
        data[address(c, r)] = str(rng.choice([rng.randint(-20, 120), rng.randint(1, 9), rng.randint(100, 5000) / 100]))

  sheets = {"Data": data}
  maker = FormulaMaker(rng, data_rows, data_cols)
  names = ["Calc", "Report", "Summary"][:rng.choice([1, 2, 2, 3])]
  formula_cells = []
  for sheet in names:
    maker.sheet = sheet
    cells = {}
    rows = rng.randint(4, 12)
    cols = rng.randint(2, 5)
    for r in range(1, rows + 1):
      for c in range(cols):
        if rng.random() < 0.1:
          continue
        name = address(c, r)
        if rng.random() < 0.08:
          cells[name] = maker.number()
        else:
          cells[name] = "=" + maker.expr(rng.choice([1, 2, 2, 3]))
          formula_cells.append((sheet, name))
        maker.earlier.append((sheet, name))
    sheets[sheet] = cells

  # Rare defects in the workbook.
  if len(formula_cells) > 4 and rng.random() < 0.07:
    (s1, n1), (s2, n2) = rng.sample(formula_cells, 2)
    sheets[s1][n1] += f"+{s2}!{n2}"
    sheets[s2][n2] += f"-{s1}!{n1}"
  if formula_cells and rng.random() < 0.03:
    s, n = rng.choice(formula_cells)
    sheets[s][n] = f"={n}*2"
  if formula_cells and rng.random() < 0.04:
    s, n = rng.choice(formula_cells)
    sheets[s][n] = rng.choice([f"=Archive!B2+{maker.number()}", f"=SUMX({maker.data_range()})", "=AB3+1"])
  if formula_cells and rng.random() < 0.04:
    s, n = rng.choice(formula_cells)
    sheets[s][n] = rng.choice(["=A1+*2", "=SUM(Data!A1:B2", '="open', "=3 $ 4"])

  requests = [f"{s}!{n}" for s, n in rng.sample(formula_cells, min(len(formula_cells), rng.randint(6, 14)))]
  if rng.random() < 0.1:
    requests.append(rng.choice(["Data!A1", f"{names[0]}!H50", "Nowhere!A1"]))
  return {"sheets": sheets, "requests": requests}
