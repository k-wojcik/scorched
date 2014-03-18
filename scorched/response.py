import json
import scorched.dates


class SolrFacetCounts(object):
    members = (
        "facet_dates",
        "facet_fields",
        "facet_queries",
        "facet_pivot"
    )

    def __init__(self, **kwargs):
        for member in self.members:
            setattr(self, member, kwargs.get(member, ()))
        self.facet_fields = dict(self.facet_fields)

    @classmethod
    def from_response(cls, response):
        facet_counts = dict(response.get("facet_counts", {}))
        return SolrFacetCounts(**facet_counts)

    @classmethod
    def from_response_json(cls, response):
        try:
            facet_counts = response['facet_counts']
        except KeyError:
            return SolrFacetCounts()
        facet_fields = {}
        for facet_field, facet_values in facet_counts[
                'facet_fields'].items():
            facets = []
            # Change each facet list from [a, 1, b, 2, c, 3 ...] to
            # [(a, 1), (b, 2), (c, 3) ...]
            for n, value in enumerate(facet_values):
                if n & 1 == 0:
                    name = value
                else:
                    facets.append((name, value))
            facet_fields[facet_field] = facets
        facet_counts['facet_fields'] = facet_fields
        return SolrFacetCounts(**facet_counts)


class SolrResponse(object):

    @classmethod
    def from_json(cls, jsonmsg, datefields=()):
        self = cls()
        self.original_json = jsonmsg
        doc = json.loads(jsonmsg)
        details = doc['responseHeader']
        for attr in ["QTime", "params", "status"]:
            setattr(self, attr, details.get(attr))
        if self.status != 0:
            raise ValueError("Response indicates an error")
        self.result = SolrResult()
        if doc.get('response'):
            self.result = SolrResult.from_json(doc['response'], datefields)
        # TODO mlt/ returns match what should we do with it ?
        #if doc.get('match'):
        #    self.result = SolrResult.from_json(doc['match'], datefields)
        self.facet_counts = SolrFacetCounts.from_response_json(doc)
        self.highlighting = doc.get("highlighting", {})
        self.groups = doc.get('grouped', {})
        self.more_like_these = dict((k, SolrResult.from_json(v, datefields))
                                    for (k, v) in doc.get('moreLikeThis', {}
                                                          ).items())
        # can be computed by MoreLikeThisHandler
        self.interesting_terms = doc.get('interestingTerms', None)
        return self

    def __str__(self):
        return str(self.result)

    def __len__(self):
        return len(self.result.docs)

    def __getitem__(self, key):
        return self.result.docs[key]


class SolrResult(object):

    @classmethod
    def from_json(cls, node, datefields=()):
        self = cls()
        self.name = 'response'
        self.numFound = int(node['numFound'])
        self.start = int(node['start'])
        docs = node['docs']
        self.docs = self._prepare_docs(docs, datefields)
        return self

    def _prepare_docs(self, docs, datefields):
        for doc in docs:
            for name, value in doc.items():
                if name in datefields:
                    doc[name] = scorched.dates.solr_date(value)._dt_obj
                elif name.endswith(datefields):
                    doc[name] = scorched.dates.solr_date(value)._dt_obj
        return docs

    def __str__(self):
        return "%(numFound)s results found, starting at #%(start)s\n\n" % (
            self.__dict__ + str(self.docs))