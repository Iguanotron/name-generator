"""Parser for language files."""

import yaml

from generator import language

# TODO use weak references for better garbage collecting with disconnected languages


def unzip(l):
    return zip(*l)


def make_form_placeholder(v):
    if isinstance(v, list):
        return language.ProbabilisticForm([], [])
    if not isinstance(v, str):
        raise ValueError('Non-string form expression in tag')
    if v.startswith('('): # concatenation
        if not v.endswith(')'):
            raise ValueError('Unmatched parenthesis in tagged form expression: %s' % v)
        return language.ConcatenativeForm([])
    if v.startswith('$'): # tag
        raise ValueError('Tag at top level in tagged form expression: %s' % v)
    # literal
    return language.LiteralForm(v)


def get_yaml_data(filename):
    try:
        with open(filename, 'r') as f:
            return yaml.load(f)
    except yaml.error.YAMLError as e:
        raise ValueError('Improperly formatted YAML file') from e


def parse_forms(forms, tagged_forms, root):
    """Parse the forms in the given forms table.
    Return the Form generated by the given root form string.
    Params:
        forms : dict of form expressions, indexed by tag
        tagged_forms : dict of Form, indexed by tag
        root : str, form expression
    """
    def parse_form_exp(exp):
        if not isinstance(exp, str):
            raise ValueError('Non-string form expression')
        if exp.startswith('('): # concatenation
            if not exp.endswith(')'):
                raise ValueError('Unmatched parenthesis in form expression: %s' % exp)
            return language.ConcatenativeForm([
                parse_form_exp(s) for s in exp[1:-1].split()
            ])
        if exp.startswith('$'): # tag
            try:
                return tagged_forms[exp[1:]]
            except KeyError:
                raise ValueError('Unknown tag in form expression: %s' % exp)
        # literal
        return language.LiteralForm(exp)

    def parse_probabilistic_form_clause(s):
        elements = s.split(maxsplit=1)
        try:
            odds = int(elements[0])
            return parse_form_exp(elements[1]), odds
        except (ValueError, IndexError):
            return parse_form_exp(s.strip()), 1

    # parse root form
    root_form = parse_form_exp(root)

    # parse tagged forms
    for tag, form in tagged_forms.items():
        if isinstance(form, language.ProbabilisticForm):
            form.set_forms(*unzip(map(parse_probabilistic_form_clause, forms[tag])))
        elif isinstance(form, language.ConcatenativeForm):
            form.set_forms(parse_form_exp(forms[tag]).forms)

    return root_form


def load_language_file(filename):
    """Load a language from a file."""
    data = get_yaml_data(filename)
    try:
        name = data['name']
        root = data['root']
        forms = data.get('forms', {})
    except KeyError as e:
        raise ValueError('Missing required field: %s' % e.args[0])

    if not isinstance(name, str):
        raise ValueError('Non-string language name')
    if not isinstance(forms, dict):
        raise ValueError('Tagged forms table not a dictionary')
    
    tagged_forms = {k: make_form_placeholder(v) for k, v in forms.items()}

    root_form = parse_forms(forms, tagged_forms, root)

    return language.Language(name, root_form)


def load_metalanguage_file(filename):
    """Load a metalanguage from a file."""
    data = get_yaml_data(filename)
    try:
        name = data['name']
        root = data['out']
        forms = data.get('forms', {})
        in_tag = data['in']
        priority = data['priority']
    except KeyError as e:
        raise ValueError('Missing required field: %s' % e.args[0])

    if not isinstance(name, str):
        raise ValueError('Non-string metalanguage name')
    if not isinstance(in_tag, str):
        raise ValueError('Non-string input form tag')
    if not isinstance(priority, int):
        raise ValueError('Non-integer priority')
    if not isinstance(forms, dict):
        raise ValueError('Tagged forms table not a dictionary')

    tagged_forms = {k: make_form_placeholder(v) for k, v in forms.items()}
    in_form = language.VariableForm('$UNSET')
    tagged_forms[in_tag] = in_form

    root_form = parse_forms(forms, tagged_forms, root)

    return language.Metalanguage(name, root_form, priority, in_form)