from app.ecommerce.repository import PublicCatalogRepository
from app.ecommerce.schemas import BranchList, ProductList


class PublicCatalogService:
    def __init__(self, repository: PublicCatalogRepository):
        self.repository = repository

    def branches(self):
        return BranchList(branches=self.repository.branches())

    def products(self, q="", branch_id=None):
        return ProductList(products=self.repository.products(q.strip(), branch_id))

    def product(self, product_id):
        return self.repository.products(product_id=product_id)[0]
