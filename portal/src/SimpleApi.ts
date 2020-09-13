import {
    Affidavit,
    AnalysisSearchResult,
    LocalSearchResult,
    OCDSBuyer,
    OCDSBuyerWithSuppliers,
    OCDSItemPriceEvolutionResponse,
    OCDSItemRelatedParty,
    OCDSItemResult,
    OCDSPaginatedResult,
    OCDSSupplierContract,
    OCDSSupplierResult,
    OCDSSuppliersPaginatedResult,
    PaginatedResult,
    SimpleAPINotPaginatedResult
} from './Model';

const BASE_API = "https://datapy.cds.com.py/api";
//const BASE_API = "http://localhost:3001/api";

export class SimpleApi {

    async findPeople(query: string): Promise<LocalSearchResult> {
        const d = await fetch(`${BASE_API}/find?query=${query}`);
        return await d.json();
    }

    async findPeopleInAnalysis(query: string): Promise<AnalysisSearchResult> {
        const d = await fetch(`${BASE_API}/findAnalysis?query=${query}`);
        return await d.json();
    }

    async getItems(pagination: { page: number, pageSize: number }): Promise<OCDSPaginatedResult> {
        const d = await fetch(`${BASE_API}/ocds/items?page=${pagination.page}&size=${pagination.pageSize}`);
        return await d.json();
    }

    async getSuppliers(pagination: { page: number, pageSize: number }): Promise<OCDSSuppliersPaginatedResult> {
        const d = await fetch(`${BASE_API}/ocds/suppliers?page=${pagination.page}&size=${pagination.pageSize}`);
        return await d.json();
    }

    async getSupplier(ruc: string): Promise<OCDSSupplierResult> {
        const d = await fetch(`${BASE_API}/ocds/suppliers/${ruc}`);
        return await d.json();
    }

    async getItemInfo(itemId: string): Promise<OCDSItemResult> {
        const d = await fetch(`${BASE_API}/ocds/items/${itemId}`);
        return await d.json();
    }

    async getItemPriceEvolution(id: string): Promise<OCDSItemPriceEvolutionResponse> {
        const d = await fetch(`${BASE_API}/ocds/items/${id}/evolution`);
        return await d.json();
    }

    async getItemParties(id: string): Promise<SimpleAPINotPaginatedResult<OCDSItemRelatedParty>> {
        const d = await fetch(`${BASE_API}/ocds/items/${id}/parties`);
        return await d.json();
    }

    async getSupplierContracts(ruc: string, pagination: { page: number, pageSize: number }): Promise<PaginatedResult<OCDSSupplierContract>> {
        const d = await fetch(`${BASE_API}/ocds/suppliers/${ruc}/contracts?page=${pagination.page}&size=${pagination.pageSize}`);
        return await d.json();
    }

    async getDeclarationsOf(document: string): Promise<PaginatedResult<Affidavit>> {

        const d = await fetch(`${BASE_API}/people/${document}/declarations`);
        return await d.json();
    }

    async getAllDeclarations(page: number, size: number): Promise<PaginatedResult<Affidavit>> {

        const d = await fetch(`${BASE_API}/contralory/declarations?page=${page}&size=${size}`);
        return await d.json();
    }

    async getBuyerInfo(buyerId: string): Promise<{ data: OCDSBuyer }> {
        const d = await fetch(`${BASE_API}/ocds/buyer/${buyerId}`);
        return await d.json();
    }

    async getSuppliersByBuyer(buyerId: string): Promise<SimpleAPINotPaginatedResult<OCDSBuyerWithSuppliers>> {
        const d = await fetch(`${BASE_API}/ocds/buyer/${buyerId}/suppliers`);
        return await d.json();
    }

}
