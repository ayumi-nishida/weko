import React from "react";
import moment from "moment";

import * as bridge_params from "../../Bridge";
import * as config from "../../Config";

import { AppContext } from '../../Context';
import { prepareSuccessMsg, JSONToCSVConvertor } from "../../Common";

class ResultTab extends React.Component {
    static contextType = AppContext;

    prepareDisplayStatus = (status, importType, error_id) => {
        let msg = '';
        switch (status) {
            case "PENDING":
                msg = bridge_params.to_do_label;
                break;
            case "SUCCESS":
                msg = prepareSuccessMsg(importType);
                break;
            case "FAILURE":
                msg = bridge_params.error_label + ': '
                    + (error_id === 'delete_author_link' ?
                        bridge_params.delete_author_link_error :
                        bridge_params.import_fail_error
                    );
                break;
            default:
                break;
        }
        return msg;
    }

    handleDownload = async () => {
        const { tasks } = this.context;
        const data = tasks.map((task, key) => {
            return {
                [bridge_params.no_label]: key + 1,
                [bridge_params.start_date_label]: task.start_date ? task.start_date : '',
                [bridge_params.end_date_label]: task.end_date ? task.end_date : '',
                [bridge_params.weko_id_label]: task.record_id || '',
                [bridge_params.name_label]: task.fullname.join('\n'),
                [bridge_params.status_label]: this.prepareDisplayStatus(task.status, task.type, task.error_id)
            }
        })
        try {
            const response = await fetch(
                bridge_params.entrypoints.result_download,
                {
                    method: "POST",
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        json: data
                    }),
                }
            );

            const blob = await response.blob();
            const blob_text = await blob.text();
            if (blob_text.length === 45 && data){
                JSONToCSVConvertor(data, 'Creator_List_Download_' + moment().format("YYYYDDMM"), true);
            } else if (response.ok) {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'Creator_List_Download_' + moment().format("YYYYMMDDhhmm") + '.tsv';
                a.click();
                window.URL.revokeObjectURL(url);
            }
        } catch (error) {
            console.log(error);
        }
    }
    handlePageChange = async (pageNumber) => {
        const { maxPage, setErrorMessage, setCurrentPage } = this.context;
        if (!pageNumber) {
            return;
        }
        if (pageNumber < 1 || pageNumber > maxPage) {
            return;
        }
        setCurrentPage(pageNumber);
    };

    handleDownloadForPrefix = async () => {
        const { tasks, isTarget } = this.context;
        const data = tasks.map((task, key) => {
            return {
                [bridge_params.no_label]: key + 1,
                [bridge_params.start_date_label]: task.start_date ? task.start_date : '',
                [bridge_params.end_date_label]: task.end_date ? task.end_date : '',
                [bridge_params.scheme_label]: task.scheme || '',
                [bridge_params.scheme_name_label]: task.name || '',
                [bridge_params.status_label]: this.prepareDisplayStatus(task.status, task.type, task.error_id)
            }
        })
        if (data) {
            const target = isTarget === "Id_Prefix" ? "ID_Prefix" : "Affiliation_Id";
            JSONToCSVConvertor(data, target +'_List_Download_' + moment().format("YYYYDDMM"), true);
        }
    }

    renderTableItem = (tasks) => {
        const { currentPage } = this.context;
        const start = (currentPage - 1) * config.PAGE_SIZE;
        const end = currentPage * config.PAGE_SIZE;
        tasks = tasks.slice(start, end);
        return tasks.map((task, key) => {
            return (
                <tr key={key}>
                    <td>{start + key + 1}</td>
                    <td>{task.start_date ? task.start_date : ''}</td>
                    <td>{task.end_date ? task.end_date : ''}</td>
                    <td>{task.record_id || ''}</td>
                    <td>
                        {
                            task.fullname.map(name => {
                                return (<span key={key} className="newline">{name}</span>);
                            })
                        }
                    </td>
                    <td>
                        {this.prepareDisplayStatus(task.status, task.type, task.error_id)}
                    </td>
                </tr>
            )
        });
    };

    renderTableItemForPrefix = (tasks) => {
        return tasks.map((task, key) => {
            return (
                <tr key={key}>
                    <td>{key + 1}</td>
                    <td>{task.start_date ? task.start_date : ''}</td>
                    <td>{task.end_date ? task.end_date : ''}</td>
                    <td>{task.scheme || ''}</td>
                    <td>{task.name || ''}</td>
                    <td>
                        {this.prepareDisplayStatus(task.status, task.type, task.error_id)}
                    </td>
                </tr>
            )
        });
    };

    render() {
        const { tasks, recordNames, importStatus, isTarget, currentPage, maxPage,
            total, success, failure, pending  } = this.context;

        let download_method;
        let columns=[];
        let renderTable;
        if (isTarget === "author_db") {
            download_method = this.handleDownload;
            columns.push(bridge_params.weko_id_label);
            columns.push(bridge_params.name_label);
            renderTable = this.renderTableItem(tasks, recordNames);
        }else if(isTarget === "id_prefix" || isTarget === "affiliation_id"){
            download_method = this.handleDownloadForPrefix;
            columns.push(bridge_params.scheme_label);
            columns.push(
                bridge_params.scheme_name_label
            );
            renderTable = this.renderTableItemForPrefix(tasks);
        }

        return (
            <div className="result_container row">
                <div className="col-md-12 text-center">
                    <div className="row block-summary">
                    　  {isTarget === "author_db" &&
                            <div className="col-lg-2 col-md-3 col-sm-3">
                                <h3><b>{bridge_params.summary}</b></h3>
                                <div className="flex-box">
                                    <div>{bridge_params.total_label}:</div>
                                    <div>{total}</div>
                                </div>
                                <div className="flex-box">
                                    <div>{bridge_params.success_label}:</div>
                                    <div>{success}</div>
                                </div>
                                <div className="flex-box">
                                    <div>{bridge_params.failure_label}:</div>
                                    <div>{failure}</div>
                                </div>
                                <div className="flex-box">
                                    <div>{bridge_params.pending_label}:</div>
                                    <div>{pending}</div>
                                </div>
                            </div>
                        }
                        <div className="col-md-12 text-align-right">
                            <button
                                className="btn btn-primary"
                                onClick={download_method}
                                disabled={importStatus === config.IMPORT_STATUS.IMPORTING}>
                                <span className="glyphicon glyphicon-cloud-download icon"></span>{bridge_params.download_label}
                            </button>
                        </div>
                    </div>
                </div>
                <div className="col-md-12 m-t-20">
                    <table className="table table-striped table-bordered">
                        <thead>
                            <tr>
                                <th>{bridge_params.no_label}</th>
                                <th className="start_date"><p className="t_head">{bridge_params.start_date_label}</p></th>
                                <th className="end_date"><p className="t_head ">{bridge_params.end_date_label}</p></th>
                                {columns.map((column, index) => (
                                    <th>{column}</th>
                                ))}
                                <th><p className="table-title-100">{bridge_params.status_label}</p></th>
                            </tr>
                        </thead>
                        <tbody>
                            {renderTable}
                        </tbody>
                    </table>
                    <div>
                    　{isTarget === "author_db" &&
                            <Pagination
                            currentPage={currentPage}
                            totalPages={maxPage}
                            onPageChange={this.handlePageChange}
                            />
                        }
                    </div>
                </div>
            </div>
        )
    }
}

class Pagination extends React.Component {
    render() {
        const { currentPage, totalPages, onPageChange } = this.props;

        const pageNumbers = [];
        const startPage = Math.max(1, currentPage - 5);
        const endPage = Math.min(totalPages, currentPage + 4);

        for (let i = startPage; i <= endPage; i++) {
            pageNumbers.push(i);
        }

        return (
            <div className="col-sm-12 col-md-12 alignCenter">
                <ul className="pagination">
                    <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                        <a onClick={() => onPageChange(currentPage - 1)} className="page-link">
                            &lt;
                        </a>
                    </li>
                    {pageNumbers.map(number => (
                        <li key={number} className={`page-item ${number === currentPage ? 'active' : ''}`}>
                            <a onClick={() => onPageChange(number)} className="page-link">
                                {number}
                            </a>
                        </li>
                    ))}
                    <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                        <a onClick={() => onPageChange(currentPage + 1)} className="page-link">
                            &gt;
                        </a>
                    </li>
                </ul>
            </div>
        );
    }
}
export default ResultTab;
