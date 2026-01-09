INSERT INTO public.workflow_action (status, created, updated, id, action_name, action_desc, action_endpoint, action_version, action_makedate, action_lastdate, action_is_need_agree) VALUES
('N', '2025-12-01 19:24:07.265157', '2025-12-01 19:24:07.265161', 1, 'Start', 'Indicates that the action has started.', 'begin_action', '1.0.0', '2018-05-15 00:00:00', '2018-05-15 00:00:00', 'f'),
('N', '2025-12-01 19:24:07.265163', '2025-12-01 19:24:07.265164', 2, 'End', 'Indicates that the action has been completed.', 'end_action', '1.0.0', '2018-05-15 00:00:00', '2018-05-15 00:00:00', 'f'),
('N', '2025-12-01 19:24:07.265166', '2025-12-01 19:24:07.265167', 3, 'Item Registration', 'Registering items.', 'item_login', '1.0.1', '2018-05-22 00:00:00', '2018-05-22 00:00:00', 'f'),
('N', '2025-12-01 19:24:07.265169', '2025-12-01 19:24:07.26517', 4, 'Approval', 'Approval action for approval requested items.', 'approval', '2.0.0', '2018-02-11 00:00:00', '2018-02-11 00:00:00', 'f'),
('N', '2025-12-01 19:24:07.265172', '2025-12-01 19:24:07.265173', 5, 'Item Link', 'Plug-in for link items.', 'item_link', '1.0.1', '2018-05-22 00:00:00', '2018-05-22 00:00:00', 'f'),
('N', '2025-12-01 19:24:07.265175', '2025-12-01 19:24:07.265176', 6, 'OA Policy Confirmation', 'Action for OA Policy confirmation.', 'oa_policy', '1.0.0', '2019-03-15 00:00:00', '2019-03-15 00:00:00', 'f'),
('N', '2025-12-01 19:24:07.265178', '2025-12-01 19:24:07.265179', 7, 'Identifier Grant', 'Select DOI issuing organization and CNRI.', 'identifier_grant', '1.0.0', '2019-03-15 00:00:00', '2019-03-15 00:00:00', 'f'); 
